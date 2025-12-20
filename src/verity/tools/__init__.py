"""
Verity Tools - Capa de ejecución determinista

NO importes agentes legacy.
NO ejecutes código generado por LLM.
Solo tools versionadas con schemas.
"""

from verity.tools.base import BaseTool, ToolDefinition

__all__ = [
    "BaseTool",
    "ToolDefinition",
]
