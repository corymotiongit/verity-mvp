"""
Verity Core - Núcleo inmutable del sistema

NOTA: Este módulo contiene tanto la nueva arquitectura como legacy Gemini API.
Los nuevos componentes están en subdirectorios (intent_resolver/, agent_policy/, etc.)

El core NO sabe de forecasting, OCR, charts especiales ni lógica de negocio.

Componentes nuevos:
- intent_resolver: Clasifica intención del usuario (LLM ligero)
- agent_policy: Autoriza ejecución de tools (sin autonomía)
- tool_registry: Registro central de tools disponibles
- schema_validator: Valida inputs/outputs contra schemas
- tool_executor: Ejecuta tools (local/HTTP/gRPC)
- checkpoint_logger: Log inmutable de cada ejecución
- response_composer: Explica resultados (LLM controlado)

Legacy (mantener por compatibilidad):
- gemini: Gemini Developer API integration
"""

from verity.core.gemini import (
    get_gemini_client,
    create_file_search_store,
    get_file_search_store,
    delete_file_search_store,
    upload_to_file_search_store,
    search_in_store,
    generate_with_store,
    get_or_create_file_search_store,
    search_with_file_search,
    generate_with_context,
)

__all__ = [
    # Legacy Gemini API
    "get_gemini_client",
    "create_file_search_store",
    "get_file_search_store",
    "delete_file_search_store",
    "upload_to_file_search_store",
    "search_in_store",
    "generate_with_store",
    "get_or_create_file_search_store",
    "search_with_file_search",
    "generate_with_context",
]
