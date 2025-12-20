"""
Verity Tools - Herramientas deterministas de ejecución

Las tools:
- Son la ÚNICA forma de ejecutar lógica
- Son deterministas (o explícitamente semi-deterministas)
- Tienen schemas estrictos (input/output)
- Son versionadas
- Son testeables en aislamiento

El agente NO ejecuta.
Las tools ejecutan TODO.
"""

from verity.core.tool_registry import ToolDefinition
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Clase base para todas las tools.
    
    Cada tool debe:
    - Declarar su definición (ToolDefinition)
    - Implementar execute()
    - Ser determinista o declarar explícitamente que no lo es
    """
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Retorna la definición de la tool."""
        pass
    
    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Ejecuta la tool.
        
        Args:
            input_data: Input validado contra schema
        
        Returns:
            Output que cumple schema de salida
        """
        pass


__all__ = ["BaseTool", "ToolDefinition"]
