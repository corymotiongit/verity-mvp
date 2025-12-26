"""
Pipeline - Orquestador maestro del flujo de ejecución

Responsabilidad:
- Orquestar flujo completo: Intent → Policy → Tools → Checkpoints → Response
- NO ejecutar lógica de negocio
- NO tomar decisiones sobre datos
- Solo coordinar componentes

Flujo inmutable:
1. IntentResolver: Clasificar intención
2. AgentPolicy: Validar permisos
3. Tool Execution: Ejecutar tools según intent
4. CheckpointLogger: Loggear cada paso
5. ResponseComposer: Generar explicación

Si este flujo cambia, la arquitectura se rompe.
"""

from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from verity.core.intent_resolver import IntentResolver, Intent
from verity.core.agent_policy import AgentPolicy
from verity.core.tool_registry import ToolRegistry
from verity.core.schema_validator import SchemaValidator
from verity.core.tool_executor import ToolExecutor
from verity.core.checkpoint_logger import CheckpointLogger, Checkpoint, CheckpointStorage
from verity.core.response_composer import ResponseComposer
from verity.exceptions import VerityException
from verity.observability import get_metrics_store


@dataclass
class PipelineResult:
    """Resultado del pipeline completo."""
    conversation_id: str
    response: str
    checkpoints: list[Checkpoint]
    intent: Intent
    confidence: float


class VerityPipeline:
    """
    Orquestador maestro del sistema.
    
    Conecta todos los componentes según el flujo inmutable.
    """
    
    def __init__(
        self,
        agent_policy: AgentPolicy,
        tool_registry: ToolRegistry,
        checkpoint_storage: CheckpointStorage
    ):
        self.agent_policy = agent_policy
        self.tool_registry = tool_registry
        self.checkpoint_logger = CheckpointLogger(checkpoint_storage)
        self.tool_executor = ToolExecutor()
        self.intent_resolver = IntentResolver()
        self.response_composer = ResponseComposer()
        self.schema_validator = SchemaValidator()
    
    async def execute(
        self,
        question: str,
        context: Optional[dict[str, Any]] = None,
        conversation_id: str | None = None,
    ) -> PipelineResult:
        """
        Ejecuta el pipeline completo.
        
        Args:
            question: Pregunta del usuario
            context: Contexto adicional (tablas disponibles, etc.)
        
        Returns:
            PipelineResult con respuesta y checkpoints
        """
        conversation_id = str(conversation_id) if conversation_id else str(uuid4())
        checkpoints: list[Checkpoint] = []
        
        # Paso 1: Resolver intención
        intent_resolution = self.intent_resolver.resolve(question)
        
        # Paso 2: Determinar tools a ejecutar según intent
        tools_to_execute = self._map_intent_to_tools(intent_resolution.intent)
        
        # Paso 3: Validar permisos
        for tool_name in tools_to_execute:
            self.agent_policy.validate_or_raise(tool_name)
        
        # Paso 4: Ejecutar tools y loggear checkpoints
        last_output = None
        
        for tool_name in tools_to_execute:
            # Obtener definición de la tool
            name, version = tool_name.split("@")
            tool_def = self.tool_registry.get(name, version)
            
            # Preparar input (puede depender de output anterior)
            tool_input = self._prepare_tool_input(
                tool_name,
                question,
                context,
                last_output,
                intent_resolution.intent
            )
            
            # Validar input
            self.schema_validator.validate_input(tool_input, tool_def.input_schema)
            
            # Ejecutar
            try:
                import time
                start_time = time.time()
                
                tool_output = await self.tool_executor.execute(tool_def, tool_input)
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Validar output
                self.schema_validator.validate_output(tool_output, tool_def.output_schema)
                
                # Loggear checkpoint
                checkpoint_tool_name = (
                    "semantic_resolution" if tool_name == "resolve_semantics@1.0" else tool_name
                )
                self.checkpoint_logger.log(
                    conversation_id=conversation_id,
                    tool=checkpoint_tool_name,
                    input_data=tool_input,
                    output_data=tool_output,
                    status="ok",
                    execution_time_ms=execution_time_ms
                )
                
                # Record metrics
                get_metrics_store().record_tool_latency(tool_name, execution_time_ms)
                
                # Guardar checkpoint
                checkpoints.append(self.checkpoint_logger.get_by_conversation(conversation_id)[-1])
                
                last_output = tool_output
                
            except Exception as e:
                # Loggear error
                checkpoint_tool_name = (
                    "semantic_resolution" if tool_name == "resolve_semantics@1.0" else tool_name
                )
                self.checkpoint_logger.log(
                    conversation_id=conversation_id,
                    tool=checkpoint_tool_name,
                    input_data=tool_input,
                    output_data={"error": str(e)},
                    status="error"
                )

                # Guardar checkpoint de error para trazabilidad
                checkpoints.append(self.checkpoint_logger.get_by_conversation(conversation_id)[-1])

                # Adjuntar trazas mínimas al error tipado para que el caller
                # pueda validar que NO se ejecutaron tools posteriores.
                if isinstance(e, VerityException):
                    from dataclasses import asdict

                    # Record error metrics
                    get_metrics_store().record_tool_error(tool_name, e.code)

                    details = e.details if isinstance(e.details, dict) else {}
                    details = {**details}
                    details.setdefault("conversation_id", conversation_id)
                    details.setdefault("checkpoints", [asdict(cp) for cp in checkpoints])
                    e.details = details
                else:
                    # Record generic error
                    get_metrics_store().record_tool_error(tool_name, type(e).__name__)
                
                raise
        
        # Paso 5: Componer respuesta
        response = await self.response_composer.compose(
            user_question=question,
            checkpoints=checkpoints,
            additional_context=context
        )
        
        return PipelineResult(
            conversation_id=conversation_id,
            response=response,
            checkpoints=checkpoints,
            intent=intent_resolution.intent,
            confidence=intent_resolution.confidence
        )
    
    def _map_intent_to_tools(self, intent: Intent) -> list[str]:
        """
        Mapea intent a lista de tools a ejecutar.
        
        Este mapeo es DETERMINISTA, no usa LLM.
        """
        if intent == Intent.QUERY_DATA or intent == Intent.AGGREGATE_METRICS:
            return [
                "resolve_semantics@1.0",
                "run_table_query@1.0"
            ]
        elif intent == Intent.COMPARE_PERIODS:
            return [
                "resolve_semantics@1.0",
                "run_table_query@1.0",
                "build_chart@2.0"
            ]
        elif intent == Intent.FORECAST:
            return [
                "resolve_semantics@1.0",
                "run_table_query@1.0",
                "compute_forecast@1.0"
            ]
        elif intent == Intent.EXPLAIN_DATA:
            # Solo explicación, sin tools
            return []
        else:
            return []
    
    def _prepare_tool_input(
        self,
        tool_name: str,
        question: str,
        context: Optional[dict],
        previous_output: Optional[dict],
        intent: Intent
    ) -> dict[str, Any]:
        """
        Prepara input para una tool.
        
        Puede usar output de tool anterior (chaining).
        """
        if tool_name == "resolve_semantics@1.0":
            return {
                "question": question,
                "intent": intent.value,
                "data_dictionary_version": "latest",
                "available_tables": context.get("available_tables", []) if context else []
            }
        
        elif tool_name == "run_table_query@1.0":
            if not previous_output:
                raise ValueError("run_table_query requires previous resolve_semantics output")
            
            # Usar output de resolve_semantics
            metrics_data = previous_output.get("metrics", [])
            tables = previous_output.get("tables", [])
            filters = previous_output.get("filters", [])
            group_by = previous_output.get("group_by", []) or []
            time_column = previous_output.get("time_column")
            time_grain = previous_output.get("time_grain")
            baseline_period = previous_output.get("baseline_period")
            compare_period = previous_output.get("compare_period")
            
            # Extraer requires de todas las métricas
            all_requires = []
            for metric in metrics_data:
                all_requires.extend(metric.get("requires", []))
            
            # Preparar métricas para run_table_query
            metrics_input = [
                {
                    "name": m["name"],
                    "sql": m["definition"]
                }
                for m in metrics_data
            ]

            # Orden temporal por defecto si hay group_by y no se especificó otro
            order_by = []
            if group_by:
                order_by = [{"column": group_by[0], "direction": "ASC"}]
            
            return {
                "table": tables[0] if tables else "orders",
                "columns": list(set(all_requires)),
                "metrics": metrics_input,
                "filters": filters,
                "group_by": group_by,
                "order_by": order_by,
                "limit": 1000,
                # Campos opcionales para compare-periods (run_table_query los interpreta determinísticamente)
                "time_column": time_column,
                "time_grain": time_grain,
                "baseline_period": baseline_period,
                "compare_period": compare_period,
            }
        
        elif tool_name == "build_chart@2.0":
            if not previous_output:
                raise ValueError("build_chart requires previous run_table_query output")
            
            return {
                "table_id": previous_output["table_id"],
                "chart_kind": "bar",  # Hard-coded por intent
                "x_axis": previous_output["columns"][0],
                "y_axes": previous_output["columns"][1:],
                "title": question
            }
        
        return {}


__all__ = ["VerityPipeline", "PipelineResult"]
