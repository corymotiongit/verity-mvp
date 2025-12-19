"""Verity Core Module - Gemini Developer API integration."""

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
