"""
Verity Tags - Service

Business logic for tag management with audit trail.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from verity.auth.schemas import User
from verity.exceptions import NotFoundException, ValidationException
from .schemas import (
    TagCreate, TagUpdate, TagResponse, TagListResponse,
    DocumentTagAssignment, DocumentTagsResponse,
    CollectionCreate, CollectionUpdate, CollectionResponse, CollectionListResponse,
    BulkTagAction, BulkMoveAction, BulkCategoryAction, BulkActionResult,
    CollectionFilter
)

logger = logging.getLogger(__name__)

# =============================================================================
# In-Memory Storage (Replace with DB in production)
# =============================================================================

# Structure: {org_id: {tag_id: tag_data}}
_tags_store: dict[str, dict[str, dict]] = {}

# Structure: {org_id: {document_id: [tag_ids]}}
_document_tags_store: dict[str, dict[str, list[str]]] = {}

# Structure: {org_id: {collection_id: collection_data}}
_collections_store: dict[str, dict[str, dict]] = {}

# Audit log: list of audit entries
_audit_log: list[dict] = []

# Persistence paths
TAGS_STORE_PATH = Path("uploads/tags_store.json")
DOCUMENT_TAGS_PATH = Path("uploads/document_tags.json")
COLLECTIONS_PATH = Path("uploads/collections.json")
AUDIT_LOG_PATH = Path("uploads/tags_audit.json")


def _load_stores():
    """Load stores from disk on module import."""
    global _tags_store, _document_tags_store, _collections_store, _audit_log
    
    if TAGS_STORE_PATH.exists():
        with open(TAGS_STORE_PATH) as f:
            _tags_store = json.load(f)
    
    if DOCUMENT_TAGS_PATH.exists():
        with open(DOCUMENT_TAGS_PATH) as f:
            _document_tags_store = json.load(f)
    
    if COLLECTIONS_PATH.exists():
        with open(COLLECTIONS_PATH) as f:
            _collections_store = json.load(f)
    
    if AUDIT_LOG_PATH.exists():
        with open(AUDIT_LOG_PATH) as f:
            _audit_log = json.load(f)


def _save_stores():
    """Persist stores to disk."""
    TAGS_STORE_PATH.parent.mkdir(exist_ok=True)
    
    with open(TAGS_STORE_PATH, "w") as f:
        json.dump(_tags_store, f, indent=2, default=str)
    
    with open(DOCUMENT_TAGS_PATH, "w") as f:
        json.dump(_document_tags_store, f, indent=2, default=str)
    
    with open(COLLECTIONS_PATH, "w") as f:
        json.dump(_collections_store, f, indent=2, default=str)
    
    with open(AUDIT_LOG_PATH, "w") as f:
        json.dump(_audit_log[-1000:], f, indent=2, default=str)  # Keep last 1000


# Load on import
_load_stores()


# =============================================================================
# Audit Trail
# =============================================================================

def _audit(action: str, entity_type: str, entity_id: str, user: User, details: dict = None):
    """Log an audit entry."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "user_id": str(user.id),
        "org_id": str(user.org_id),
        "details": details or {}
    }
    _audit_log.append(entry)
    logger.info(f"[AUDIT] {action} {entity_type} {entity_id} by {user.id}")


# =============================================================================
# Tags Service
# =============================================================================

class TagsService:
    """
    Manages tags with organization scope and audit trail.
    
    Tags are:
    - Scoped by org_id (never cross-org)
    - Created/modified by admin/editor roles only
    - Assigned to documents with audit trail
    """
    
    # -------------------------------------------------------------------------
    # Tag CRUD
    # -------------------------------------------------------------------------
    
    async def list_tags(self, user: User) -> TagListResponse:
        """List all tags for the user's organization."""
        org_id = str(user.org_id)
        org_tags = _tags_store.get(org_id, {})
        
        items = []
        for tag_id, tag_data in org_tags.items():
            # Count documents with this tag
            doc_count = self._count_documents_with_tag(org_id, tag_id)
            items.append(TagResponse(
                id=UUID(tag_id),
                org_id=UUID(org_id),
                name=tag_data["name"],
                color=tag_data.get("color"),
                document_count=doc_count,
                created_by=UUID(tag_data["created_by"]) if tag_data.get("created_by") else None,
                created_at=datetime.fromisoformat(tag_data["created_at"])
            ))
        
        # Sort by name
        items.sort(key=lambda t: t.name.lower())
        
        return TagListResponse(items=items, total=len(items))
    
    async def get_tag(self, tag_id: UUID, user: User) -> TagResponse:
        """Get a specific tag."""
        org_id = str(user.org_id)
        tag_id_str = str(tag_id)
        
        org_tags = _tags_store.get(org_id, {})
        if tag_id_str not in org_tags:
            raise NotFoundException("tag", tag_id)
        
        tag_data = org_tags[tag_id_str]
        doc_count = self._count_documents_with_tag(org_id, tag_id_str)
        
        return TagResponse(
            id=tag_id,
            org_id=UUID(org_id),
            name=tag_data["name"],
            color=tag_data.get("color"),
            document_count=doc_count,
            created_by=UUID(tag_data["created_by"]) if tag_data.get("created_by") else None,
            created_at=datetime.fromisoformat(tag_data["created_at"])
        )
    
    async def create_tag(self, data: TagCreate, user: User) -> TagResponse:
        """Create a new tag."""
        org_id = str(user.org_id)
        
        # Initialize org store if needed
        if org_id not in _tags_store:
            _tags_store[org_id] = {}
        
        # Check for duplicate name
        for existing in _tags_store[org_id].values():
            if existing["name"].lower() == data.name.lower():
                raise ValidationException(f"Tag '{data.name}' already exists")
        
        tag_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        tag_data = {
            "name": data.name,
            "color": data.color,
            "created_by": str(user.id),
            "created_at": now.isoformat()
        }
        
        _tags_store[org_id][tag_id] = tag_data
        _save_stores()
        
        _audit("create", "tag", tag_id, user, {"name": data.name})
        
        return TagResponse(
            id=UUID(tag_id),
            org_id=UUID(org_id),
            name=data.name,
            color=data.color,
            document_count=0,
            created_by=user.id,
            created_at=now
        )
    
    async def update_tag(self, tag_id: UUID, data: TagUpdate, user: User) -> TagResponse:
        """Update an existing tag."""
        org_id = str(user.org_id)
        tag_id_str = str(tag_id)
        
        org_tags = _tags_store.get(org_id, {})
        if tag_id_str not in org_tags:
            raise NotFoundException("tag", tag_id)
        
        tag_data = org_tags[tag_id_str]
        changes = {}
        
        if data.name is not None and data.name != tag_data["name"]:
            # Check for duplicate name
            for tid, existing in org_tags.items():
                if tid != tag_id_str and existing["name"].lower() == data.name.lower():
                    raise ValidationException(f"Tag '{data.name}' already exists")
            changes["name"] = {"from": tag_data["name"], "to": data.name}
            tag_data["name"] = data.name
        
        if data.color is not None:
            changes["color"] = {"from": tag_data.get("color"), "to": data.color}
            tag_data["color"] = data.color
        
        if changes:
            _save_stores()
            _audit("update", "tag", tag_id_str, user, changes)
        
        return await self.get_tag(tag_id, user)
    
    async def delete_tag(self, tag_id: UUID, user: User) -> bool:
        """Delete a tag (also removes from all documents)."""
        org_id = str(user.org_id)
        tag_id_str = str(tag_id)
        
        org_tags = _tags_store.get(org_id, {})
        if tag_id_str not in org_tags:
            raise NotFoundException("tag", tag_id)
        
        tag_name = org_tags[tag_id_str]["name"]
        
        # Remove from all documents
        if org_id in _document_tags_store:
            for doc_id, doc_tags in _document_tags_store[org_id].items():
                if tag_id_str in doc_tags:
                    doc_tags.remove(tag_id_str)
        
        # Delete tag
        del _tags_store[org_id][tag_id_str]
        _save_stores()
        
        _audit("delete", "tag", tag_id_str, user, {"name": tag_name})
        
        return True
    
    # -------------------------------------------------------------------------
    # Document Tag Assignment
    # -------------------------------------------------------------------------
    
    async def get_document_tags(self, document_id: UUID, user: User) -> DocumentTagsResponse:
        """Get tags assigned to a document."""
        org_id = str(user.org_id)
        doc_id_str = str(document_id)
        
        org_doc_tags = _document_tags_store.get(org_id, {})
        tag_ids = org_doc_tags.get(doc_id_str, [])
        
        # Resolve tag details
        org_tags = _tags_store.get(org_id, {})
        tags = []
        for tag_id in tag_ids:
            if tag_id in org_tags:
                tag_data = org_tags[tag_id]
                tags.append(TagResponse(
                    id=UUID(tag_id),
                    org_id=UUID(org_id),
                    name=tag_data["name"],
                    color=tag_data.get("color"),
                    document_count=0,  # Not computing here for performance
                    created_by=UUID(tag_data["created_by"]) if tag_data.get("created_by") else None,
                    created_at=datetime.fromisoformat(tag_data["created_at"])
                ))
        
        return DocumentTagsResponse(document_id=document_id, tags=tags)
    
    async def update_document_tags(
        self, 
        document_id: UUID, 
        data: DocumentTagAssignment, 
        user: User
    ) -> DocumentTagsResponse:
        """Add/remove tags from a document."""
        org_id = str(user.org_id)
        doc_id_str = str(document_id)
        
        # Initialize stores if needed
        if org_id not in _document_tags_store:
            _document_tags_store[org_id] = {}
        if doc_id_str not in _document_tags_store[org_id]:
            _document_tags_store[org_id][doc_id_str] = []
        
        current_tags = set(_document_tags_store[org_id][doc_id_str])
        org_tags = _tags_store.get(org_id, {})
        
        changes = {"added": [], "removed": []}
        
        # Add tags
        for tag_id in data.add_tags:
            tag_id_str = str(tag_id)
            if tag_id_str in org_tags and tag_id_str not in current_tags:
                current_tags.add(tag_id_str)
                changes["added"].append(org_tags[tag_id_str]["name"])
        
        # Remove tags
        for tag_id in data.remove_tags:
            tag_id_str = str(tag_id)
            if tag_id_str in current_tags:
                current_tags.remove(tag_id_str)
                if tag_id_str in org_tags:
                    changes["removed"].append(org_tags[tag_id_str]["name"])
        
        _document_tags_store[org_id][doc_id_str] = list(current_tags)
        _save_stores()
        
        if changes["added"] or changes["removed"]:
            _audit("update_tags", "document", doc_id_str, user, changes)
        
        return await self.get_document_tags(document_id, user)
    
    # -------------------------------------------------------------------------
    # Bulk Actions
    # -------------------------------------------------------------------------
    
    async def bulk_update_tags(self, data: BulkTagAction, user: User) -> BulkActionResult:
        """Add/remove tags from multiple documents."""
        success_count = 0
        failed_ids = []
        
        for doc_id in data.document_ids:
            try:
                await self.update_document_tags(
                    doc_id,
                    DocumentTagAssignment(add_tags=data.add_tags, remove_tags=data.remove_tags),
                    user
                )
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to update tags for {doc_id}: {e}")
                failed_ids.append(doc_id)
        
        _audit("bulk_update_tags", "documents", "batch", user, {
            "document_count": len(data.document_ids),
            "add_count": len(data.add_tags),
            "remove_count": len(data.remove_tags)
        })
        
        return BulkActionResult(
            success_count=success_count,
            failed_count=len(failed_ids),
            failed_ids=failed_ids,
            message=f"Updated tags for {success_count}/{len(data.document_ids)} documents"
        )
    
    # -------------------------------------------------------------------------
    # Collections (Saved Filters)
    # -------------------------------------------------------------------------
    
    async def list_collections(self, user: User) -> CollectionListResponse:
        """List saved collections for the organization."""
        org_id = str(user.org_id)
        org_collections = _collections_store.get(org_id, {})
        
        items = []
        for coll_id, coll_data in org_collections.items():
            # Count matching documents (simplified)
            doc_count = await self._count_collection_documents(org_id, coll_data["filter"])
            
            items.append(CollectionResponse(
                id=UUID(coll_id),
                org_id=UUID(org_id),
                name=coll_data["name"],
                description=coll_data.get("description"),
                filter=CollectionFilter(**coll_data["filter"]),
                document_count=doc_count,
                created_by=UUID(coll_data["created_by"]) if coll_data.get("created_by") else None,
                created_at=datetime.fromisoformat(coll_data["created_at"]),
                updated_by=UUID(coll_data["updated_by"]) if coll_data.get("updated_by") else None,
                updated_at=datetime.fromisoformat(coll_data["updated_at"]) if coll_data.get("updated_at") else None,
                last_used_at=datetime.fromisoformat(coll_data["last_used_at"]) if coll_data.get("last_used_at") else None
            ))
        
        items.sort(key=lambda c: c.name.lower())
        return CollectionListResponse(items=items, total=len(items))
    
    async def create_collection(self, data: CollectionCreate, user: User) -> CollectionResponse:
        """Create a saved collection (filter)."""
        org_id = str(user.org_id)
        
        if org_id not in _collections_store:
            _collections_store[org_id] = {}
        
        coll_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        coll_data = {
            "name": data.name,
            "description": data.description,
            "filter": data.filter.model_dump(),
            "created_by": str(user.id),
            "created_at": now.isoformat()
        }
        
        _collections_store[org_id][coll_id] = coll_data
        _save_stores()
        
        _audit("create", "collection", coll_id, user, {"name": data.name})
        
        return CollectionResponse(
            id=UUID(coll_id),
            org_id=UUID(org_id),
            name=data.name,
            description=data.description,
            filter=data.filter,
            document_count=0,
            created_by=user.id,
            created_at=now
        )
    
    async def delete_collection(self, collection_id: UUID, user: User) -> bool:
        """Delete a collection."""
        org_id = str(user.org_id)
        coll_id_str = str(collection_id)
        
        org_collections = _collections_store.get(org_id, {})
        if coll_id_str not in org_collections:
            raise NotFoundException("collection", collection_id)
        
        coll_name = org_collections[coll_id_str]["name"]
        del _collections_store[org_id][coll_id_str]
        _save_stores()
        
        _audit("delete", "collection", coll_id_str, user, {"name": coll_name})
        return True
    
    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    
    def _count_documents_with_tag(self, org_id: str, tag_id: str) -> int:
        """Count documents that have a specific tag."""
        count = 0
        org_doc_tags = _document_tags_store.get(org_id, {})
        for doc_tags in org_doc_tags.values():
            if tag_id in doc_tags:
                count += 1
        return count
    
    async def _count_collection_documents(self, org_id: str, filter_data: dict) -> int:
        """Count documents matching a collection filter (simplified)."""
        # This would need integration with DocumentsService for full implementation
        # For now, return 0 as placeholder
        return 0


# =============================================================================
# Singleton
# =============================================================================

_tags_service: TagsService | None = None

def get_tags_service() -> TagsService:
    """Get the tags service singleton."""
    global _tags_service
    if _tags_service is None:
        _tags_service = TagsService()
    return _tags_service
