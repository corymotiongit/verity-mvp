"""
Verity v2 API Routes - Nueva arquitectura

Endpoints que usan el nuevo pipeline:
- IntentResolver
- AgentPolicy
- Tools deterministas
- CheckpointLogger
- ResponseComposer

NO usa agentes legacy.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from uuid import uuid4

from verity.core.pipeline import VerityPipeline, PipelineResult
from verity.core.agent_policy import AgentPolicy, AgentConfig
from verity.core.tool_registry import ToolRegistry
from verity.core.checkpoint_logger import CheckpointStorage, Checkpoint
from verity.tools.resolve_semantics import ResolveSemanticsTool
from verity.tools.run_table_query import RunTableQueryTool
from verity.tools.build_chart import BuildChartTool
from verity.exceptions import AmbiguousMetricException, UnresolvedMetricException, VerityException
from verity.core.semantics_context import SemanticsContextStore


router = APIRouter(prefix="/api/v2", tags=["v2-query"])


class QueryRequest(BaseModel):
    """Request para ejecutar query usando nueva arquitectura."""
    question: str
    conversation_id: Optional[str] = None
    available_tables: list[str] = ["orders"]
    context: Optional[dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Response con resultado y checkpoints."""
    conversation_id: str
    response: str
    intent: str
    confidence: float
    checkpoints: list[dict]


# Storage simple en memoria (TODO: usar PostgreSQL/SQLite)
class InMemoryCheckpointStorage(CheckpointStorage):
    """Storage temporal de checkpoints en memoria."""
    
    def __init__(self):
        self._checkpoints: dict[str, list[Checkpoint]] = {}
    
    def save(self, checkpoint: Checkpoint) -> None:
        """Guarda checkpoint."""
        conv_id = checkpoint.conversation_id
        if conv_id not in self._checkpoints:
            self._checkpoints[conv_id] = []
        self._checkpoints[conv_id].append(checkpoint)
    
    def query(self, conversation_id: str) -> list[Checkpoint]:
        """Obtiene checkpoints por conversation_id."""
        return self._checkpoints.get(conversation_id, [])


_CHECKPOINT_STORAGE = InMemoryCheckpointStorage()
_SEMANTICS_CONTEXT = SemanticsContextStore(ttl_seconds=30 * 60)
_PIPELINE: VerityPipeline | None = None


# Inicializar componentes del pipeline
def get_pipeline() -> VerityPipeline:
    """Factory para crear pipeline configurado."""

    global _PIPELINE
    if _PIPELINE is not None:
        return _PIPELINE
    
    # Configurar agente policy
    agent_config = AgentConfig(
        agent_id="data_analyst",
        allowed_tools=[
            "resolve_semantics",
            "run_table_query",
            "build_chart"
        ],
        addons_enabled=[]
    )
    agent_policy = AgentPolicy(agent_config)
    
    # Configurar tool registry
    tool_registry = ToolRegistry()
    
    # Registrar tools
    resolve_semantics_tool = ResolveSemanticsTool()
    run_table_query_tool = RunTableQueryTool()
    build_chart_tool = BuildChartTool()
    
    tool_registry.register(resolve_semantics_tool.definition)
    tool_registry.register(run_table_query_tool.definition)
    tool_registry.register(build_chart_tool.definition)
    
    # Configurar checkpoint storage (persistente in-process)
    checkpoint_storage = _CHECKPOINT_STORAGE
    
    # Crear pipeline
    pipeline = VerityPipeline(
        agent_policy=agent_policy,
        tool_registry=tool_registry,
        checkpoint_storage=checkpoint_storage
    )
    
    # Registrar handlers locales para tools
    pipeline.tool_executor.register_local_handler(
        "resolve_semantics@1.0",
        resolve_semantics_tool.execute
    )
    pipeline.tool_executor.register_local_handler(
        "run_table_query@1.0",
        run_table_query_tool.execute
    )
    pipeline.tool_executor.register_local_handler(
        "build_chart@2.0",
        build_chart_tool.execute
    )
    
    _PIPELINE = pipeline
    return _PIPELINE


def _format_disambiguation_prompt(candidates: list[dict[str, Any]]) -> str:
    # Prompt corto, 1 turno.
    lines = ["¿A cuál métrica te refieres? Responde con el número (1-5) o el nombre exacto:"]
    for i, c in enumerate(candidates[:5], start=1):
        metric = c.get("metric")
        alias = c.get("matched_alias")
        score = c.get("score")
        if metric and alias:
            lines.append(f"{i}) {metric} (alias: {alias}, score: {score})")
        elif metric:
            lines.append(f"{i}) {metric}")
    return "\n".join(lines)


def _maybe_apply_disambiguation_answer(*, conversation_id: str, question: str) -> str:
    ctx = _SEMANTICS_CONTEXT.get(conversation_id)
    pending = ctx.pending_candidates or []
    qn = (question or "").strip()
    if not pending:
        return question

    # Opción 1: número
    if qn.isdigit():
        idx = int(qn)
        if 1 <= idx <= min(5, len(pending)):
            chosen = pending[idx - 1]
            metric = chosen.get("metric")
            if isinstance(metric, str) and metric.strip():
                _SEMANTICS_CONTEXT.clear_pending_candidates(conversation_id=conversation_id)
                return metric.strip()

    # Opción 2: nombre canónico
    for c in pending[:5]:
        metric = c.get("metric")
        if isinstance(metric, str) and metric.strip() and metric.strip().lower() == qn.lower():
            _SEMANTICS_CONTEXT.clear_pending_candidates(conversation_id=conversation_id)
            return metric.strip()

    return question


@router.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest) -> QueryResponse:
    """
    Ejecuta query usando el nuevo pipeline v2.
    
    Flujo:
    1. IntentResolver clasifica intención
    2. AgentPolicy valida permisos
    3. Tools se ejecutan según intent
    4. Checkpoints se loggean
    5. ResponseComposer genera explicación
    
    Returns:
        QueryResponse con respuesta y checkpoints
    """
    try:
        # Crear pipeline
        pipeline = get_pipeline()

        # conversation_id estable (para contexto + checkpoints)
        conversation_id = request.conversation_id or str(uuid4())

        # Si venimos de una ambigüedad, aceptar respuesta (1 turno)
        question = _maybe_apply_disambiguation_answer(conversation_id=conversation_id, question=request.question)
        
        # Preparar contexto
        context = request.context or {}
        context["available_tables"] = request.available_tables
        # Contexto conversacional leve: último metric/table resueltos
        conv_ctx = _SEMANTICS_CONTEXT.get(conversation_id)
        context["conversation_context"] = {
            "last_metric": conv_ctx.last_metric,
            "last_table": conv_ctx.last_table,
            "last_alias": conv_ctx.last_alias,
        }
        
        # Ejecutar pipeline
        result: PipelineResult = await pipeline.execute(
            question=question,
            context=context,
            conversation_id=conversation_id,
        )
        
        # Convertir checkpoints a dict
        from dataclasses import asdict
        checkpoints_dict = [asdict(cp) for cp in result.checkpoints]

        # Actualizar contexto conversacional con la última resolución semántica exitosa
        try:
            sem_cp = next(
                (cp for cp in result.checkpoints if cp.tool == "semantic_resolution" and cp.status == "ok"),
                None,
            )
            if sem_cp and isinstance(sem_cp.output, dict):
                metrics = sem_cp.output.get("metrics")
                tables = sem_cp.output.get("tables")
                if isinstance(metrics, list) and metrics and isinstance(metrics[0], dict):
                    metric_name = metrics[0].get("name")
                    alias = metrics[0].get("alias_matched")
                else:
                    metric_name = None
                    alias = None
                if isinstance(tables, list) and tables and isinstance(tables[0], str):
                    table_name = tables[0]
                else:
                    table_name = None
                _SEMANTICS_CONTEXT.set_last_resolution(
                    conversation_id=conversation_id,
                    metric=str(metric_name) if metric_name else None,
                    table=str(table_name) if table_name else None,
                    alias=str(alias) if alias else None,
                )
        except Exception:
            # Best-effort only
            pass
        
        return QueryResponse(
            conversation_id=conversation_id,
            response=result.response,
            intent=result.intent.value,
            confidence=result.confidence,
            checkpoints=checkpoints_dict
        )

    except AmbiguousMetricException as e:
        details = e.details if isinstance(e.details, dict) else {}
        conv_id = str(details.get("conversation_id") or request.conversation_id or str(uuid4()))
        candidates = details.get("candidates") if isinstance(details.get("candidates"), list) else []
        checkpoints = details.get("checkpoints") if isinstance(details.get("checkpoints"), list) else []

        # Guardar opciones para 1 turno
        if candidates:
            _SEMANTICS_CONTEXT.set_pending_candidates(conversation_id=conv_id, candidates=candidates[:5])

        return QueryResponse(
            conversation_id=conv_id,
            response=_format_disambiguation_prompt(candidates),
            intent="aggregate",
            confidence=0.2,
            checkpoints=checkpoints,
        )

    except UnresolvedMetricException:
        # Mantener contrato actual (error tipado) para unresolved.
        raise
    
    except VerityException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health")
async def health_check():
    """Health check del pipeline v2."""
    return {
        "status": "ok",
        "version": "2.0",
        "architecture": "tool-based",
        "components": [
            "IntentResolver",
            "AgentPolicy",
            "ToolRegistry",
            "ToolExecutor",
            "CheckpointLogger",
            "ResponseComposer"
        ]
    }
