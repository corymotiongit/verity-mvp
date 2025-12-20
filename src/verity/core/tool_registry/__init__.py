"""
Tool Registry - Registro central de tools disponibles

Responsabilidad:
- Registrar tools con metadata (nombre, version, schemas)
- Proveer acceso a definiciones de tools
- NO ejecutar tools
- NO validar datos (eso es schema_validator)

Cada tool declara:
- nombre
- versión
- input_schema (JSON Schema)
- output_schema (JSON Schema)
- determinista o no
- modo de ejecución (local, http, grpc)
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class ToolDefinition:
    """Definición completa de una tool."""
    name: str
    version: str
    input_schema: dict          # JSON Schema
    output_schema: dict         # JSON Schema
    is_deterministic: bool
    execution_mode: Literal["local", "http", "grpc"]
    endpoint: Optional[str] = None     # Solo si es remoto
    timeout_ms: int = 30000


class ToolRegistry:
    """
    Registro central de tools.
    
    El core no sabe cómo se ejecutan las tools.
    Solo conoce sus contratos (schemas).
    """
    
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
    
    def register(self, tool: ToolDefinition) -> None:
        """
        Registra una tool.
        
        Args:
            tool: Definición de la tool
        
        Raises:
            ValueError: Si la tool ya está registrada
        """
        key = f"{tool.name}@{tool.version}"
        if key in self._tools:
            raise ValueError(f"Tool {key} already registered")
        self._tools[key] = tool
    
    def get(self, name: str, version: str) -> ToolDefinition:
        """
        Obtiene definición de una tool.
        
        Args:
            name: Nombre de la tool
            version: Versión de la tool
        
        Returns:
            ToolDefinition
        
        Raises:
            KeyError: Si la tool no existe
        """
        key = f"{name}@{version}"
        if key not in self._tools:
            raise KeyError(f"Tool {key} not found")
        return self._tools[key]
    
    def list_tools(self) -> list[str]:
        """
        Lista todas las tools registradas.
        
        Returns:
            Lista de nombres con versión (formato: "name@version")
        """
        return list(self._tools.keys())


__all__ = ["ToolDefinition", "ToolRegistry"]
