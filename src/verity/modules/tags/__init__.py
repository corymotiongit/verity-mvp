"""
Verity Tags Module

Tag management with:
- Organization-scoped tags
- Document tag assignments
- Saved collections (filter presets)
- Bulk actions
- Full audit trail
"""

from .router import router
from .schemas import (
    TagCreate, TagUpdate, TagResponse, TagListResponse,
    DocumentTagAssignment, DocumentTagsResponse,
    CollectionCreate, CollectionUpdate, CollectionResponse, CollectionListResponse,
    CollectionFilter,
    BulkTagAction, BulkMoveAction, BulkCategoryAction, BulkActionResult,
    DocumentMetadataExtended, DocumentCategory
)
from .service import TagsService, get_tags_service

__all__ = [
    "router",
    "TagsService",
    "get_tags_service",
    "TagCreate",
    "TagUpdate", 
    "TagResponse",
    "TagListResponse",
    "DocumentTagAssignment",
    "DocumentTagsResponse",
    "CollectionCreate",
    "CollectionUpdate",
    "CollectionResponse",
    "CollectionListResponse",
    "CollectionFilter",
    "BulkTagAction",
    "BulkMoveAction",
    "BulkCategoryAction",
    "BulkActionResult",
    "DocumentMetadataExtended",
    "DocumentCategory",
]
