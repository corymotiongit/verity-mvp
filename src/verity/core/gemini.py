"""
Verity Core - Gemini Developer API Integration.

Uses Gemini Developer API (API key) with File Search Tool.
Supports multi-organization with isolated File Search stores.
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

from verity.config import get_settings
from verity.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)

_client = None


def _get_api_key() -> str:
    """
    Get Gemini API key.
    
    Resolution order:
    1. GEMINI_API_KEY environment variable
    2. .env.local file
    3. Secret Manager (production)
    """
    # Try environment variable first
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        logger.info("Using Gemini API key from environment variable")
        return api_key
    
    # Try .env.local file
    env_local = Path(__file__).parent.parent.parent.parent / ".env.local"
    if env_local.exists():
        for line in env_local.read_text().strip().split("\n"):
            if line.startswith("GEMINI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                if api_key:
                    logger.info("Using Gemini API key from .env.local")
                    return api_key
    
    # Try Secret Manager in production
    settings = get_settings()
    if settings.is_production:
        try:
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            secret_name = f"projects/{settings.gcp.project_id}/secrets/gemini-api-key/versions/latest"
            response = client.access_secret_version(request={"name": secret_name})
            api_key = response.payload.data.decode("utf-8").strip()
            logger.info("Using Gemini API key from Secret Manager")
            return api_key
        except Exception as e:
            logger.error(f"Failed to get API key from Secret Manager: {e}")
    
    raise ExternalServiceException(
        "Gemini API",
        "No API key found. Set GEMINI_API_KEY environment variable or configure Secret Manager."
    )


def get_gemini_client():
    """
    Get configured Gemini client.
    
    Uses API key authentication (Gemini Developer API).
    """
    global _client
    
    if _client is not None:
        return _client
    
    from google import genai
    
    api_key = _get_api_key()
    _client = genai.Client(api_key=api_key)
    
    logger.info("Gemini client initialized with API key")
    return _client


def create_file_search_store(org_id: UUID, org_name: str) -> str:
    """
    Create a new File Search store for an organization.
    
    Each organization gets its own isolated store.
    
    Args:
        org_id: Organization UUID
        org_name: Organization name for display
    
    Returns:
        Store name (e.g., 'fileSearchStores/abc123')
    """
    client = get_gemini_client()
    
    display_name = f"verity-{org_name}-{str(org_id)[:8]}"
    
    try:
        store = client.file_search_stores.create(
            config={"display_name": display_name}
        )
        logger.info(f"Created File Search store for org {org_id}: {store.name}")
        return store.name
    except Exception as e:
        logger.error(f"Failed to create File Search store: {e}")
        raise ExternalServiceException("File Search", str(e))


def get_file_search_store(store_name: str) -> Any:
    """Get File Search store by name."""
    client = get_gemini_client()
    
    try:
        return client.file_search_stores.get(name=store_name)
    except Exception as e:
        logger.error(f"Failed to get File Search store: {e}")
        raise ExternalServiceException("File Search", str(e))


def delete_file_search_store(store_name: str) -> None:
    """Delete a File Search store."""
    client = get_gemini_client()
    
    try:
        client.file_search_stores.delete(name=store_name, config={"force": True})
        logger.info(f"Deleted File Search store: {store_name}")
    except Exception as e:
        logger.warning(f"Failed to delete File Search store: {e}")


def list_file_search_stores() -> list[dict]:
    """
    List all File Search stores in the account.
    
    Returns:
        List of store info dicts with name and display_name
    """
    client = get_gemini_client()
    
    try:
        stores = client.file_search_stores.list()
        result = []
        for store in stores:
            result.append({
                "name": store.name,
                "display_name": getattr(store, "display_name", None),
                "create_time": str(getattr(store, "create_time", None)),
            })
        logger.info(f"Listed {len(result)} File Search stores")
        return result
    except Exception as e:
        logger.error(f"Failed to list File Search stores: {e}")
        raise ExternalServiceException("File Search", str(e))


def list_documents_in_store(store_name: str) -> list[dict]:
    """
    List all documents in a File Search store.
    
    Args:
        store_name: Store name (e.g., 'fileSearchStores/abc123')
    
    Returns:
        List of document info dicts
    """
    client = get_gemini_client()
    
    try:
        # The API method is fileSearchStores.documents.list
        documents = client.file_search_stores.documents.list(
            parent=store_name
        )
        result = []
        for doc in documents:
            result.append({
                "name": doc.name,
                "display_name": getattr(doc, "display_name", None),
                "state": str(getattr(doc, "state", None)),
                "create_time": str(getattr(doc, "create_time", None)),
                "update_time": str(getattr(doc, "update_time", None)),
            })
        logger.info(f"Listed {len(result)} documents in store {store_name}")
        return result
    except Exception as e:
        logger.error(f"Failed to list documents in store: {e}")
        raise ExternalServiceException("File Search", str(e))


def delete_document_from_store(document_name: str) -> bool:
    """
    Delete a document from a File Search store.
    
    Args:
        document_name: Full document name (e.g., 'fileSearchStores/abc/documents/xyz')
    
    Returns:
        True if deleted successfully
    """
    client = get_gemini_client()
    
    try:
        client.file_search_stores.documents.delete(name=document_name)
        logger.info(f"Deleted document from File Search: {document_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise ExternalServiceException("File Search", str(e))


def upload_to_file_search_store(
    file_path: str,
    display_name: str,
    store_name: str,
    metadata: dict | None = None,
) -> dict:
    """
    Upload a file to a specific File Search store.
    
    Args:
        file_path: Path to the file to upload
        display_name: Display name for the file (visible in citations)
        store_name: Target store name
        metadata: Optional custom metadata (e.g., {"category": "contrato"})
    
    Returns:
        Dict with upload metadata
    """
    import time
    
    client = get_gemini_client()
    
    try:
        logger.info(f"Uploading file to store {store_name}: {file_path}")
        
        # Build config with optional metadata
        config = {"display_name": display_name}
        
        # Add custom metadata if provided
        custom_metadata = []
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (int, float)):
                    custom_metadata.append({"key": key, "numeric_value": value})
                else:
                    custom_metadata.append({"key": key, "string_value": str(value)})
        
        # Note: The Gemini File Search API doesn't support custom_metadata on import_file
        # We'll store metadata locally in our document record instead
        # This is tracked in our document service and used for filtering
        
        # Always use direct upload to store - metadata filtering happens locally
        operation = client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=store_name,
            config=config,
        )
        
        # Wait for processing to complete
        max_wait = 120
        waited = 0
        while not operation.done and waited < max_wait:
            time.sleep(3)
            waited += 3
            operation = client.operations.get(operation)
        
        logger.info(f"File uploaded: {display_name} -> {store_name}")
        if metadata:
            logger.info(f"Metadata will be stored locally: {metadata}")
        
        return {
            "store_name": store_name,
            "display_name": display_name,
            "status": "ready" if operation.done else "processing",
            "metadata": metadata,  # Return metadata to be stored in local db
        }
        
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise ExternalServiceException("File Search Upload", str(e))


def search_in_store(
    query: str,
    store_name: str,
    model: str = "gemini-2.5-flash",
) -> dict:
    """
    Search documents in a specific File Search store.
    
    Args:
        query: Search query
        store_name: Store to search in
        model: Model to use
    
    Returns:
        Dict with response text and sources
    """
    from google.genai import types
    
    client = get_gemini_client()
    
    try:
        logger.info(f"Searching in store {store_name}: {query[:50]}...")
        
        response = client.models.generate_content(
            model=model,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_name]
                        )
                    )
                ]
            ),
        )
        
        sources = _extract_sources(response)
        
        return {
            "text": response.text,
            "sources": sources,
            "model": model,
        }
        
    except Exception as e:
        logger.error(f"File Search failed: {e}")
        raise ExternalServiceException("File Search", str(e))


def generate_with_store(
    prompt: str,
    store_name: str | None = None,
    model: str = "gemini-2.5-flash",
    metadata_filter: str | None = None,
) -> dict:
    """
    Generate content with optional File Search grounding.
    
    Args:
        prompt: User prompt
        store_name: Optional store for grounding
        model: Model to use
        metadata_filter: Optional filter for documents (e.g., "category=contrato")
    
    Returns:
        Dict with response text, sources, and metadata
    """
    from google.genai import types
    
    client = get_gemini_client()
    
    try:
        config = None
        if store_name:
            file_search_config = {
                "file_search_store_names": [store_name],
            }
            
            # Add metadata filter if provided
            if metadata_filter:
                file_search_config["metadata_filter"] = metadata_filter
                logger.info(f"Using metadata filter: {metadata_filter}")
            
            config = types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(**file_search_config)
                    )
                ]
            )
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        
        sources = _extract_sources(response) if store_name else []
        
        return {
            "text": response.text,
            "sources": sources,
            "model": model,
            "grounded": bool(store_name),
            "filter_applied": metadata_filter,
        }
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise ExternalServiceException("Gemini", str(e))


def _extract_sources(response) -> list[dict]:
    """Extract sources from Gemini response grounding metadata."""
    sources = []
    
    if not response.candidates or len(response.candidates) == 0:
        return sources
    
    candidate = response.candidates[0]
    if not hasattr(candidate, "grounding_metadata") or not candidate.grounding_metadata:
        logger.info("No grounding_metadata in response")
        return sources
    
    metadata = candidate.grounding_metadata
    
    # Log metadata structure for debugging
    logger.info(f"Grounding metadata attributes: {[a for a in dir(metadata) if not a.startswith('_')]}")
    
    # First try grounding_supports which has the actual content segments
    support_contents = []
    if hasattr(metadata, "grounding_supports") and metadata.grounding_supports:
        logger.info(f"Found {len(metadata.grounding_supports)} grounding_supports")
        for i, support in enumerate(metadata.grounding_supports):
            content = ""
            relevance = 0.0
            
            # Get the text segment
            if hasattr(support, "segment") and support.segment:
                seg = support.segment
                if hasattr(seg, "text"):
                    content = str(seg.text)[:300]
            
            # Get confidence score
            if hasattr(support, "confidence_scores") and support.confidence_scores:
                scores = support.confidence_scores
                relevance = float(scores[0]) if scores else 0.0
            
            support_contents.append({
                "content": content,
                "relevance": relevance,
            })
    
    # Get grounding chunks for titles/URIs
    if hasattr(metadata, "grounding_chunks") and metadata.grounding_chunks:
        logger.info(f"Found {len(metadata.grounding_chunks)} grounding_chunks")
        for i, chunk in enumerate(metadata.grounding_chunks):
            title = None
            content = ""
            uri = None
            
            # Log chunk structure
            chunk_attrs = [a for a in dir(chunk) if not a.startswith('_')]
            logger.info(f"Chunk {i} attrs: {chunk_attrs}")
            
            # Check for retrieved_context (File Search results)
            if hasattr(chunk, "retrieved_context") and chunk.retrieved_context:
                ctx = chunk.retrieved_context
                title = getattr(ctx, "title", None)
                uri = getattr(ctx, "uri", None)
                if not title and uri:
                    # Extract filename from URI
                    title = uri.split("/")[-1] if "/" in uri else uri
            
            # Check for web chunk
            if hasattr(chunk, "web") and chunk.web:
                web = chunk.web
                title = getattr(web, "title", None) or getattr(web, "uri", None)
            
            # Get content from support_contents if available
            relevance = 0.0
            if i < len(support_contents):
                content = support_contents[i]["content"]
                relevance = support_contents[i]["relevance"]
            
            sources.append({
                "type": "document",
                "title": title or uri or "Documento",
                "content": content,
                "uri": uri,
                "relevance": relevance,
            })
    
    # If still no sources but we have search_entry_point, extract from there
    if not sources and hasattr(metadata, "search_entry_point") and metadata.search_entry_point:
        sources.append({
            "type": "document",
            "title": "Resultado de busqueda",
            "content": str(metadata.search_entry_point)[:200],
        })
    
    logger.info(f"Extracted {len(sources)} sources from response")
    return sources


# =============================================================================
# Legacy compatibility functions (for MVP without DB)
# =============================================================================

_default_store_name = None


def get_or_create_file_search_store(display_name: str = "verity-default") -> str:
    """Get or create default store (for MVP without multi-org)."""
    global _default_store_name
    
    if _default_store_name:
        return _default_store_name
    
    client = get_gemini_client()
    
    # Check if store exists
    try:
        for store in client.file_search_stores.list():
            if store.display_name == display_name:
                _default_store_name = store.name
                return store.name
    except Exception as e:
        logger.warning(f"Error listing stores: {e}")
    
    # Create new store
    try:
        store = client.file_search_stores.create(
            config={"display_name": display_name}
        )
        _default_store_name = store.name
        logger.info(f"Created default File Search store: {store.name}")
        return store.name
    except Exception as e:
        logger.error(f"Failed to create store: {e}")
        raise ExternalServiceException("File Search", str(e))


def search_with_file_search(
    query: str,
    store_names: list[str] | None = None,
    model: str = "gemini-2.5-flash",
) -> dict:
    """Search with File Search (legacy compatibility)."""
    if store_names:
        store_name = store_names[0]
    else:
        store_name = get_or_create_file_search_store()
    
    return search_in_store(query, store_name, model)


def generate_with_context(
    prompt: str,
    context: str | None = None,
    use_file_search: bool = True,
    store_names: list[str] | None = None,
    model: str = "gemini-2.5-flash",
) -> dict:
    """Generate with context (legacy compatibility)."""
    full_prompt = prompt
    if context:
        full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}"
    
    store_name = None
    if use_file_search:
        if store_names:
            store_name = store_names[0]
        else:
            try:
                store_name = get_or_create_file_search_store()
            except Exception:
                pass
    
    return generate_with_store(full_prompt, store_name, model)
