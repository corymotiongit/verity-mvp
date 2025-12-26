import pytest

from verity.core.agent_policy import AgentConfig, AgentPolicy
from verity.core.pipeline import VerityPipeline
from verity.core.checkpoint_logger import Checkpoint, CheckpointStorage
from verity.core.intent_resolver import Intent, IntentResolution
from verity.core.tool_registry import ToolRegistry
from verity.exceptions import AmbiguousMetricException, UnresolvedMetricException
from verity.tools.resolve_semantics import ResolveSemanticsTool
from verity.tools.run_table_query import RunTableQueryTool


class InMemoryStorage(CheckpointStorage):
    def __init__(self):
        self._items: dict[str, list[Checkpoint]] = {}

    def save(self, checkpoint: Checkpoint) -> None:
        self._items.setdefault(checkpoint.conversation_id, []).append(checkpoint)

    def query(self, conversation_id: str) -> list[Checkpoint]:
        return self._items.get(conversation_id, [])

    def all_checkpoints(self) -> list[Checkpoint]:
        out: list[Checkpoint] = []
        for cps in self._items.values():
            out.extend(cps)
        return out


@pytest.mark.asyncio
async def test_reproducciones_resolves_to_total_plays():
    """Verifica que 'reproducciones' resuelve a total_plays con confidence < 1.0"""
    tool = ResolveSemanticsTool()

    out = await tool.execute(
        {
            "question": "reproducciones",
            "available_tables": ["listening_history"],
        }
    )

    assert out["metrics"], "expected at least one metric"
    assert out["metrics"][0]["name"] == "total_plays"
    assert 0 <= out["confidence"] <= 1


@pytest.mark.asyncio
async def test_total_is_ambiguous_requires_clarification():
    """Verifica que 'total' dispara ambigüedad (total_plays vs total_listening_time)"""
    tool = ResolveSemanticsTool()

    with pytest.raises(AmbiguousMetricException) as excinfo:
        await tool.execute(
            {
                "question": "total",
                "available_tables": ["listening_history"],
            }
        )

    assert excinfo.value.code == "AMBIGUOUS_METRIC"
    assert excinfo.value.details
    assert "candidates" in excinfo.value.details
    assert len(excinfo.value.details["candidates"]) >= 2


@pytest.mark.asyncio
async def test_nonexistent_metric_raises_unresolved_metric():
    tool = ResolveSemanticsTool()

    with pytest.raises(UnresolvedMetricException) as excinfo:
        await tool.execute(
            {
                "question": "profit margin",
                "available_tables": ["listening_history"],
            }
        )

    assert excinfo.value.code == "UNRESOLVED_METRIC"


@pytest.mark.asyncio
async def test_pipeline_does_not_execute_data_on_semantic_failure():
    storage = InMemoryStorage()
    tool_registry = ToolRegistry()

    resolve_tool = ResolveSemanticsTool()
    run_tool = RunTableQueryTool()
    tool_registry.register(resolve_tool.definition)
    tool_registry.register(run_tool.definition)

    agent_policy = AgentPolicy(
        AgentConfig(
            agent_id="data_analyst",
            allowed_tools=["resolve_semantics", "run_table_query"],
            addons_enabled=[],
        )
    )

    pipeline = VerityPipeline(
        agent_policy=agent_policy,
        tool_registry=tool_registry,
        checkpoint_storage=storage,
    )

    # Tests run without Gemini: force intent so the tool chain executes.
    pipeline.intent_resolver.resolve = lambda q: IntentResolution(
        intent=Intent.QUERY_DATA,
        confidence=1.0,
        needs=["data"],
        raw_question=q,
    )

    pipeline.tool_executor.register_local_handler(
        "resolve_semantics@1.0",
        resolve_tool.execute,
    )
    pipeline.tool_executor.register_local_handler(
        "run_table_query@1.0",
        run_tool.execute,
    )

    with pytest.raises(UnresolvedMetricException):
        await pipeline.execute(
            question="profit margin",
            context={"available_tables": ["listening_history"]},
        )

    # Asegura: solo se intentó semantic_resolution, NO run_table_query
    all_checkpoints = storage.all_checkpoints()
    assert len(all_checkpoints) == 1
    assert all_checkpoints[0].tool == "semantic_resolution"
    assert all_checkpoints[0].status == "error"
