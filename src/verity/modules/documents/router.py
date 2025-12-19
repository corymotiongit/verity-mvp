"""
Verity Documents - Router.

API endpoints for document operations.
Supports multi-organization isolation.
"""

import json
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile

from verity.auth import get_current_user
from verity.auth.schemas import User
from verity.deps import require_documents
from verity.modules.documents.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
)
from verity.modules.documents.service import DocumentsService
from verity.schemas import PaginationMeta

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[require_documents],
)

logger = logging.getLogger(__name__)


def get_service() -> DocumentsService:
    """Get documents service instance."""
    return DocumentsService()


@router.post("/ingest", response_model=DocumentResponse, status_code=201)
async def ingest_document(
    user: User = Depends(get_current_user),
    file: UploadFile = File(..., description="File to upload"),
    display_name: str | None = Form(default=None),
    metadata: str | None = Form(default=None, description="JSON metadata"),
):
    """
    Ingest a document into the organization's File Search store.
    
    - Documents are isolated by organization
    - Each org has its own File Search store
    - Store is created on first upload
    """
    service = get_service()

    parsed_metadata = None
    if metadata:
        try:
            loaded = json.loads(metadata)
            if isinstance(loaded, dict):
                parsed_metadata = loaded
            else:
                logger.warning(
                    "Ignoring non-object metadata for document ingest: type=%s",
                    type(loaded).__name__,
                )
        except json.JSONDecodeError as e:
            # Metadata is optional; don't fail ingest on bad JSON.
            logger.warning("Ignoring invalid metadata JSON for document ingest: %s", e)
    
    return await service.ingest_document(
        file=file.file,
        filename=file.filename or "document",
        mime_type=file.content_type or "application/octet-stream",
        display_name=display_name,
        metadata=parsed_metadata,
        user=user,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID, user: User = Depends(get_current_user)):
    """Get document metadata."""
    service = get_service()
    return await service.get_document(document_id, user)


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: UUID, user: User = Depends(get_current_user)):
    """Delete a document."""
    service = get_service()
    await service.delete_document(document_id, user)


@router.get("/{document_id}/tags")
async def get_document_tags(document_id: UUID, user: User = Depends(get_current_user)):
    """
    Get tags assigned to this document.
    
    Alias for GET /tags/documents/{document_id}.
    """
    from verity.modules.tags.service import get_tags_service
    tags_service = get_tags_service()
    result = await tags_service.get_document_tags(document_id, user)
    return {"document_id": str(document_id), "tags": [t.model_dump() for t in result.tags]}


@router.post("/{document_id}/tags")
async def update_document_tags(
    document_id: UUID,
    data: dict,
    user: User = Depends(get_current_user),
):
    """
    Add or remove tags from this document.
    
    Request body:
    ```json
    {
      "add_tags": ["tag-uuid-1", "tag-uuid-2"],
      "remove_tags": ["tag-uuid-3"]
    }
    ```
    
    Alias for POST /tags/documents/{document_id}.
    """
    from verity.modules.tags.service import get_tags_service
    from verity.modules.tags.schemas import DocumentTagAssignment
    
    tags_service = get_tags_service()
    
    assignment = DocumentTagAssignment(
        add_tags=[UUID(t) for t in data.get("add_tags", [])],
        remove_tags=[UUID(t) for t in data.get("remove_tags", [])]
    )
    
    result = await tags_service.update_document_tags(document_id, assignment, user)
    return {"document_id": str(document_id), "tags": [t.model_dump() for t in result.tags]}

@router.get("/{document_id}/download")
async def download_document(document_id: UUID, user: User = Depends(get_current_user)):
    """
    Download a document file.
    
    Returns the file for viewing/downloading.
    """
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    service = get_service()
    doc = await service.get_document(document_id, user)
    
    # Get local path from document data
    doc_data = service._documents.get(str(document_id))
    if not doc_data or not doc_data.get("local_path"):
        from verity.exceptions import NotFoundException
        raise NotFoundException("document file", document_id)
    
    local_path = Path(doc_data["local_path"])
    if not local_path.exists():
        from verity.exceptions import NotFoundException
        raise NotFoundException("document file", document_id)
    
    return FileResponse(
        path=local_path,
        filename=doc.display_name,
        media_type=doc.mime_type,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user: User = Depends(get_current_user),
    page_size: int = 20,
    page_token: str | None = None,
):
    """List documents in user's organization."""
    service = get_service()
    docs, next_token, total = await service.list_documents(user, page_size, page_token)
    return DocumentListResponse(
        items=docs,
        meta=PaginationMeta(
            total_count=total,
            page_size=page_size,
            next_page_token=next_token,
            has_more=next_token is not None,
        ),
    )


@router.post("/tags/batch")
async def batch_update_document_tags(data: dict, user: User = Depends(get_current_user)):
    """
    Batch add/remove tags from multiple documents.
    
    Request body:
    ```json
    {
      "document_ids": ["doc-uuid-1", "doc-uuid-2"],
      "add_tags": ["tag-uuid-1"],
      "remove_tags": ["tag-uuid-2"]
    }
    ```
    
    Returns:
    ```json
    {
      "success_count": 2,
      "failed_count": 0,
      "failed_ids": [],
      "message": "Updated tags for 2/2 documents"
    }
    ```
    """
    from verity.modules.tags.service import get_tags_service
    from verity.modules.tags.schemas import BulkTagAction
    
    tags_service = get_tags_service()
    
    action = BulkTagAction(
        document_ids=[UUID(d) for d in data.get("document_ids", [])],
        add_tags=[UUID(t) for t in data.get("add_tags", [])],
        remove_tags=[UUID(t) for t in data.get("remove_tags", [])]
    )
    
    result = await tags_service.bulk_update_tags(action, user)
    return result.model_dump()


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(request: DocumentSearchRequest, user: User = Depends(get_current_user)):
    """
    Search documents using File Search.
    
    - Searches only in user's organization's store
    - Returns results with sources
    """
    service = get_service()
    request_id = uuid4()
    return await service.search_documents(request, user, request_id)


@router.get("/store/info")
async def get_store_info(user: User = Depends(get_current_user)):
    """
    Get File Search store info for the organization.
    
    Returns the store ID and list of indexed documents from Google.
    """
    from verity.core.gemini import list_documents_in_store
    
    store_id = None
    if user.organization and user.organization.file_search_store_id:
        store_id = user.organization.file_search_store_id
    
    if not store_id:
        return {
            "store_id": None,
            "documents": [],
            "document_count": 0,
            "message": "No File Search store configured for this organization"
        }
    
    try:
        docs = list_documents_in_store(store_id)
        return {
            "store_id": store_id,
            "documents": docs,
            "document_count": len(docs),
        }
    except Exception as e:
        return {
            "store_id": store_id,
            "documents": [],
            "document_count": 0,
            "error": str(e)
        }


@router.get("/store/filters")
async def get_store_filters(user: User = Depends(get_current_user)):
    """
    Get unique categories, projects, and tags from all documents.
    
    Returns lists of unique values for dynamic filtering in the UI.
    """
    from verity.modules.documents.service import _documents
    
    org_id = str(user.org_id)
    
    categories = set()
    projects = set()
    tags = set()
    
    # Collect unique values from all documents in this org
    for doc in _documents.values():
        if doc.get("org_id") != org_id:
            continue
        
        metadata = doc.get("metadata", {})
        if metadata:
            if metadata.get("category"):
                categories.add(metadata["category"])
            if metadata.get("project"):
                projects.add(metadata["project"])
            if metadata.get("tags"):
                # Tags might be comma-separated string or list
                doc_tags = metadata["tags"]
                if isinstance(doc_tags, str):
                    for tag in doc_tags.split(","):
                        tags.add(tag.strip())
                elif isinstance(doc_tags, list):
                    for tag in doc_tags:
                        tags.add(tag.strip())
    
    return {
        "categories": sorted(list(categories)),
        "projects": sorted(list(projects)),
        "tags": sorted(list(tags)),
    }
