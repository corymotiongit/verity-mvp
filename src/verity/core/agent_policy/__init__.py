"""
Agent Policy - Control de permisos de ejecución

Responsabilidad:
- Validar si el agente puede ejecutar una tool
- NO ejecutar nada
- NO tomar decisiones de negocio
- Solo enforcement de permisos

El agente NO es un ente autónomo.
El agente ES una configuración declarativa.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class AgentConfig:
    """Configuración declarativa del agente."""
    agent_id: str
    allowed_tools: list[str]
    addons_enabled: list[str]


class AgentPolicy:
    """
    Policy enforcement para autorización de tools.
    
    El agente:
    - NO ejecuta
    - NO decide datos
    - NO tiene estado
    - Solo autoriza
    """
    
    def __init__(self, config: AgentConfig):
        self.agent_id = config.agent_id
        self.allowed_tools = set(config.allowed_tools)
        self.addons_enabled = set(config.addons_enabled)
    
    def can_execute(self, tool_name: str) -> bool:
        """
        Verifica si el agente puede ejecutar la tool.
        
        Args:
            tool_name: Nombre de la tool (formato: "name@version" o "name")
        
        Returns:
            True si está permitida, False si no
        """
        base_name = tool_name.split("@")[0]
        return base_name in self.allowed_tools
    
    def validate_or_raise(self, tool_name: str) -> None:
        """
        Valida permiso de ejecución o lanza PermissionError.
        
        Args:
            tool_name: Nombre de la tool a validar
        
        Raises:
            PermissionError: Si el agente no puede ejecutar la tool
        """
        if not self.can_execute(tool_name):
            raise PermissionError(
                f"Agent '{self.agent_id}' cannot execute tool '{tool_name}'"
            )


__all__ = ["AgentConfig", "AgentPolicy"]
