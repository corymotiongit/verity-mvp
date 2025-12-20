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

from verity.core.pipeline import VerityPipeline, PipelineResult
from verity.core.agent_policy import AgentPolicy, AgentConfig
from verity.core.tool_registry import ToolRegistry
from verity.core.checkpoint_logger import CheckpointStorage, Checkpoint
from verity.tools.resolve_semantics import ResolveSemanticsTool
from verity.tools.run_table_query import RunTableQueryTool
from verity.tools.build_chart import BuildChartTool
from verity.exceptions import VerityException


router = APIRouter(prefix="/api/v2", tags=["v2-query"])


class QueryRequest(BaseModel):
    """Request para ejecutar query usando nueva arquitectura."""
    question: str
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


# Inicializar componentes del pipeline
def get_pipeline() -> VerityPipeline:
    """Factory para crear pipeline configurado."""
    
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
    
    # Configurar checkpoint storage
    checkpoint_storage = InMemoryCheckpointStorage()
    
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
    
    return pipeline


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
        
        # Preparar contexto
        context = request.context or {}
        context["available_tables"] = request.available_tables
        
        # Ejecutar pipeline
        result: PipelineResult = await pipeline.execute(
            question=request.question,
            context=context
        )
        
        # Convertir checkpoints a dict
        from dataclasses import asdict
        checkpoints_dict = [asdict(cp) for cp in result.checkpoints]
        
        return QueryResponse(
            conversation_id=result.conversation_id,
            response=result.response,
            intent=result.intent.value,
            confidence=result.confidence,
            checkpoints=checkpoints_dict
        )
    
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
