"""
Tool Executor - Ejecutor de tools con soporte multi-protocolo

Responsabilidad:
- Ejecutar tools (local / HTTP / gRPC)
- Manejar timeouts
- Manejar errores de ejecución
- NO validar schemas (eso es schema_validator)
- NO autorizar (eso es agent_policy)
- NO loggear (eso es checkpoint_logger)

El core no se acopla a la implementación de las tools.
"""

from typing import Any, Callable
import asyncio
import inspect
from verity.core.tool_registry import ToolDefinition
from verity.exceptions import VerityException


class ToolExecutionError(Exception):
    """Error durante ejecución de tool."""
    
    def __init__(self, tool: str, reason: str):
        self.tool = tool
        self.reason = reason
        super().__init__(f"Tool {tool} failed: {reason}")


class ToolExecutor:
    """
    Ejecutor universal de tools.
    
    Soporta:
    - Funciones Python locales
    - HTTP endpoints
    - gRPC services
    
    Maneja timeouts de forma consistente.
    """
    
    def __init__(self):
        self._local_handlers: dict[str, Callable] = {}
    
    def register_local_handler(self, tool_name: str, handler: Callable) -> None:
        """
        Registra handler local para una tool.
        
        Args:
            tool_name: Nombre de la tool (formato: "name@version")
            handler: Función que implementa la tool
        """
        self._local_handlers[tool_name] = handler
    
    async def execute(
        self,
        tool_def: ToolDefinition,
        input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Ejecuta una tool según su modo de ejecución.
        
        Args:
            tool_def: Definición de la tool
            input_data: Datos de entrada (ya validados)
        
        Returns:
            Resultado de la ejecución (dict)
        
        Raises:
            ToolExecutionError: Si la ejecución falla
        """
        tool_key = f"{tool_def.name}@{tool_def.version}"
        
        try:
            if tool_def.execution_mode == "local":
                return await self._execute_local(tool_key, input_data, tool_def.timeout_ms)
            elif tool_def.execution_mode == "http":
                return await self._execute_http(tool_def, input_data)
            elif tool_def.execution_mode == "grpc":
                return await self._execute_grpc(tool_def, input_data)
            else:
                raise ToolExecutionError(
                    tool_key,
                    f"Unsupported execution mode: {tool_def.execution_mode}"
                )
        except asyncio.TimeoutError as exc:
            raise ToolExecutionError(tool_key, "Timeout exceeded") from exc
        except VerityException:
            raise
        except Exception as e:
            raise ToolExecutionError(tool_key, str(e)) from e
    
    async def _execute_local(
        self,
        tool_key: str,
        input_data: dict,
        timeout_ms: int
    ) -> dict:
        """Ejecuta tool local con timeout."""
        if tool_key not in self._local_handlers:
            raise KeyError(f"No local handler for {tool_key}")
        
        handler = self._local_handlers[tool_key]

        # Aplicar timeout
        timeout_sec = timeout_ms / 1000.0

        if inspect.iscoroutinefunction(handler):
            return await asyncio.wait_for(handler(input_data), timeout=timeout_sec)

        # Handler sync: ejecutarlo en thread
        return await asyncio.wait_for(
            asyncio.to_thread(handler, input_data),
            timeout=timeout_sec,
        )
    
    async def _execute_http(self, tool_def: ToolDefinition, input_data: dict) -> dict:
        """Ejecuta tool remota vía HTTP."""
        # Stub (HTTP execution not implemented)
        raise NotImplementedError("HTTP execution - stub")
    
    async def _execute_grpc(self, tool_def: ToolDefinition, input_data: dict) -> dict:
        """Ejecuta tool remota vía gRPC."""
        # Stub (gRPC execution not implemented)
        raise NotImplementedError("gRPC execution - stub")


__all__ = ["ToolExecutor", "ToolExecutionError"]
