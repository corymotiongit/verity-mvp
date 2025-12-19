"""Verity Tags - Router.

REST API endpoints for tag management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from verity.auth import get_current_user
from verity.auth.schemas import User
from verity.modules.tags.schemas import (
    BulkActionResult,
    BulkTagAction,
    CollectionCreate,
    CollectionListResponse,
    CollectionResponse,
    DocumentTagAssignment,
    DocumentTagsResponse,
    TagCreate,
    TagListResponse,
    TagResponse,
    TagUpdate,
)
from verity.modules.tags.service import get_tags_service

router = APIRouter(prefix="/tags", tags=["Tags"])


def get_service():
    return get_tags_service()


@router.get("", response_model=TagListResponse)
async def list_tags(user: User = Depends(get_current_user)) -> TagListResponse:
    """List all tags for the organization."""
    service = get_service()
    return await service.list_tags(user)


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(data: TagCreate, user: User = Depends(get_current_user)) -> TagResponse:
    """Create a new tag."""
    service = get_service()
    return await service.create_tag(data, user)


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: UUID, user: User = Depends(get_current_user)) -> TagResponse:
    """Get a specific tag by ID."""
    service = get_service()
    return await service.get_tag(tag_id, user)


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(tag_id: UUID, data: TagUpdate, user: User = Depends(get_current_user)) -> TagResponse:
    """Update an existing tag."""
    service = get_service()
    return await service.update_tag(tag_id, data, user)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: UUID, user: User = Depends(get_current_user)):
    """Delete a tag."""
    service = get_service()
    await service.delete_tag(tag_id, user)
    return None


@router.get("/documents/{document_id}", response_model=DocumentTagsResponse)
async def get_document_tags(document_id: UUID, user: User = Depends(get_current_user)) -> DocumentTagsResponse:
    """Get all tags assigned to a document."""
    service = get_service()
    return await service.get_document_tags(document_id, user)


@router.post("/documents/{document_id}", response_model=DocumentTagsResponse)
async def update_document_tags(
    document_id: UUID,
    data: DocumentTagAssignment,
    user: User = Depends(get_current_user),
) -> DocumentTagsResponse:
    """Add/remove tags from a document."""
    service = get_service()
    return await service.update_document_tags(document_id, data, user)


@router.post("/bulk/tags", response_model=BulkActionResult)
async def bulk_update_tags(data: BulkTagAction, user: User = Depends(get_current_user)) -> BulkActionResult:
    """Bulk add/remove tags from multiple documents."""
    service = get_service()
    return await service.bulk_update_tags(data, user)


@router.get("/collections", response_model=CollectionListResponse)
async def list_collections(user: User = Depends(get_current_user)) -> CollectionListResponse:
    """List saved collections for the organization."""
    service = get_service()
    return await service.list_collections(user)


@router.post("/collections", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    data: CollectionCreate,
    user: User = Depends(get_current_user),
) -> CollectionResponse:
    """Create a saved collection (filter)."""
    service = get_service()
    return await service.create_collection(data, user)


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(collection_id: UUID, user: User = Depends(get_current_user)):
    """Delete a saved collection."""
    service = get_service()
    await service.delete_collection(collection_id, user)
    return None


@router.get("/audit")
async def get_audit_log(
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(get_current_user),
):
    """Get recent tag-related audit entries for the user's org."""
    from verity.modules.tags.service import _audit_log

    org_id = str(user.org_id)
    org_entries = [e for e in _audit_log if e.get("org_id") == org_id]
    recent = org_entries[-limit:] if len(org_entries) > limit else org_entries
    return {
        "entries": list(reversed(recent)),
        "total": len(org_entries),
        "showing": len(recent),
    }

