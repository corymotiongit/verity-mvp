"""
Verity Agent - Scope Resolver

Resolves ChatScope to actual document IDs.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from verity.auth.schemas import User
from verity.modules.agent.schemas import ChatScope, ResolvedScope, ScopeSuggestion
from verity.modules.documents.service import _documents
from verity.modules.tags.service import (
    _document_tags_store, 
    _tags_store, 
    _collections_store,
    _audit_log,
    _save_stores
)

logger = logging.getLogger(__name__)


class ScopeResolver:
    """
    Resolves a ChatScope to actual document IDs.
    
    Resolution order:
    1. If doc_ids explicit -> use those directly
    2. If collection_id -> expand collection filters
    3. Apply filters (project, tags, category, period, source)
    4. If mode='all_docs' -> return all org docs
    5. If mode='empty' -> return empty with requires_action=True
    """
    
    async def resolve(self, scope: ChatScope, user: User) -> ResolvedScope:
        """Resolve scope to document IDs."""
        org_id = str(user.org_id)
        
        # Mode: empty -> force user action
        if scope.mode == "empty":
            return ResolvedScope(
                is_empty=True,
                requires_action=True,
                display_summary="Sin scope definido - selecciona proyecto, tags o documentos"
            )
        
        # Priority 1: Explicit doc_ids
        if scope.doc_ids:
            return await self._resolve_explicit_docs(scope.doc_ids, user)
        
        # Priority 2: Collection expands to filters
        filters = await self._get_filters(scope, org_id)
        
        # Mode: all_docs -> no filtering
        if scope.mode == "all_docs":
            return await self._resolve_all_docs(user)
        
        # Apply filters
        return await self._resolve_filtered(filters, user)
    
    async def _get_filters(self, scope: ChatScope, org_id: str) -> dict:
        """Get effective filters (from collection or direct)."""
        if scope.collection_id:
            # Expand collection to filters
            coll_id_str = str(scope.collection_id)
            org_collections = _collections_store.get(org_id, {})
            
            if coll_id_str in org_collections:
                coll = org_collections[coll_id_str]
                coll_filter = coll.get("filter", {})
                
                # Update last_used_at
                coll["last_used_at"] = datetime.now(timezone.utc).isoformat()
                _save_stores()
                
                return {
                    "project": coll_filter.get("project"),
                    "tag_ids": [UUID(t) for t in coll_filter.get("tags", [])],
                    "categories": coll_filter.get("categories", []),
                    "period": coll_filter.get("period"),
                    "source": coll_filter.get("source"),
                    "collection_name": coll.get("name")
                }
        
        # Direct filters from scope
        return {
            "project": scope.project,
            "tag_ids": scope.tag_ids,
            "categories": [scope.category] if scope.category else [],
            "period": scope.period,
            "source": scope.source,
            "collection_name": None
        }
    
    async def _resolve_explicit_docs(self, doc_ids: List[UUID], user: User) -> ResolvedScope:
        """Resolve explicit document selection."""
        org_id = str(user.org_id)
        valid_docs = []
        canonical_ids = []
        
        for doc_id in doc_ids:
            doc_id_str = str(doc_id)
            if doc_id_str in _documents:
                doc = _documents[doc_id_str]
                if doc.get("org_id") == org_id:
                    valid_docs.append(doc_id)
                    # Check if has canonical version
                    if doc.get("normalization_info", {}).get("canonical_file"):
                        canonical_ids.append(doc_id)
        
        return ResolvedScope(
            doc_ids=valid_docs,
            doc_count=len(valid_docs),
            canonical_file_ids=canonical_ids,
            display_summary=f"Selección manual: {len(valid_docs)} documentos",
            is_empty=len(valid_docs) == 0
        )
    
    async def _resolve_all_docs(self, user: User) -> ResolvedScope:
        """Resolve to all org documents."""
        org_id = str(user.org_id)
        doc_ids = []
        canonical_ids = []
        
        for doc_id, doc in _documents.items():
            if doc.get("org_id") == org_id:
                doc_ids.append(UUID(doc_id))
                if doc.get("normalization_info", {}).get("canonical_file"):
                    canonical_ids.append(UUID(doc_id))
        
        return ResolvedScope(
            doc_ids=doc_ids,
            doc_count=len(doc_ids),
            canonical_file_ids=canonical_ids,
            display_summary=f"Todos los documentos: {len(doc_ids)}",
            is_empty=len(doc_ids) == 0
        )
    
    async def _resolve_filtered(self, filters: dict, user: User) -> ResolvedScope:
        """Resolve documents matching filters."""
        org_id = str(user.org_id)
        matching_docs = []
        canonical_ids = []
        tag_names = []
        
        # Get tag names for display
        org_tags = _tags_store.get(org_id, {})
        for tag_id in filters.get("tag_ids", []):
            tag_id_str = str(tag_id)
            if tag_id_str in org_tags:
                tag_names.append(org_tags[tag_id_str]["name"])
        
        # Get documents with matching tags
        docs_with_tags = set()
        if filters.get("tag_ids"):
            org_doc_tags = _document_tags_store.get(org_id, {})
            for doc_id, doc_tags in org_doc_tags.items():
                # OR logic: document matches if it has ANY of the specified tags
                for tag_id in filters["tag_ids"]:
                    if str(tag_id) in doc_tags:
                        docs_with_tags.add(doc_id)
                        break
        
        # Filter documents
        for doc_id, doc in _documents.items():
            if doc.get("org_id") != org_id:
                continue
            
            metadata = doc.get("metadata", {})
            
            # Project filter
            if filters.get("project"):
                doc_project = metadata.get("project", "")
                if doc_project.lower() != filters["project"].lower():
                    continue
            
            # Category filter
            if filters.get("categories"):
                doc_category = metadata.get("category", "")
                if doc_category not in filters["categories"]:
                    continue
            
            # Period filter
            if filters.get("period"):
                doc_period = metadata.get("period", "")
                if doc_period != filters["period"]:
                    continue
            
            # Source filter
            if filters.get("source"):
                doc_source = metadata.get("source", "")
                if doc_source.lower() != filters["source"].lower():
                    continue
            
            # Tag filter (if tags specified, doc must be in docs_with_tags)
            if filters.get("tag_ids") and doc_id not in docs_with_tags:
                continue
            
            matching_docs.append(UUID(doc_id))
            if doc.get("normalization_info", {}).get("canonical_file"):
                canonical_ids.append(UUID(doc_id))
        
        # Build display summary
        parts = []
        if filters.get("project"):
            parts.append(f"Proyecto: {filters['project']}")
        if tag_names:
            parts.append(f"Tags: {', '.join(tag_names)}")
        if filters.get("categories"):
            parts.append(f"Tipos: {', '.join(filters['categories'])}")
        if filters.get("collection_name"):
            parts.append(f"Colección: {filters['collection_name']}")
        
        summary = " + ".join(parts) if parts else "Sin filtros"
        summary += f" ({len(matching_docs)} docs)"
        
        # Diagnostic logic
        empty_reason = None
        suggestion = None
        requires_action = len(matching_docs) == 0 and filters.get("project") is None and not filters.get("tag_ids")
        
        if len(matching_docs) == 0:
            if filters.get("project"):
                # Check if project exists (has any doc)
                has_project_docs = any(
                   d.get("metadata", {}).get("project") == filters["project"] 
                   for d in _documents.values()
                   if d.get("org_id") == org_id
                )
                if not has_project_docs:
                    empty_reason = f"El proyecto '{filters['project']}' está vacío."
                    suggestion = ScopeSuggestion(
                        label=f"Subir archivo a {filters['project']}", 
                        action="upload",
                        project_id=filters["project"]
                    )
                else:
                    empty_reason = "No hay documentos que coincidan con los filtros (tags/tipo)."
                    suggestion = ScopeSuggestion(label="Quitar filtros", action="clear_filters")
            elif filters.get("tag_ids"):
                 empty_reason = "No hay documentos con los tags seleccionados."
                 suggestion = ScopeSuggestion(label="Quitar filtros", action="clear_filters")
            else:
                 if requires_action:
                     empty_reason = "No se ha seleccionado búsqueda."
                 else:
                    empty_reason = "No se encontraron documentos."
                    suggestion = ScopeSuggestion(label="Ver todos", action="select_all")

        return ResolvedScope(
            doc_ids=matching_docs,
            doc_count=len(matching_docs),
            canonical_file_ids=canonical_ids,
            display_summary=summary,
            project=filters.get("project"),
            tag_names=tag_names,
            collection_name=filters.get("collection_name"),
            is_empty=len(matching_docs) == 0,
            requires_action=requires_action,
            empty_reason=empty_reason,
            suggestion=suggestion
        )


def log_scope_change(
    conversation_id: str, 
    user: User, 
    old_scope: Optional[ChatScope], 
    new_scope: ChatScope
):
    """Audit log for scope changes."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "scope_change",
        "entity_type": "conversation",
        "entity_id": conversation_id,
        "user_id": str(user.id),
        "org_id": str(user.org_id),
        "details": {
            "old_scope": old_scope.model_dump() if old_scope else None,
            "new_scope": new_scope.model_dump()
        }
    }
    _audit_log.append(entry)
    _save_stores()
    logger.info(f"[SCOPE] Changed for conversation {conversation_id}: {new_scope.mode}")


# Singleton
_scope_resolver: ScopeResolver | None = None

def get_scope_resolver() -> ScopeResolver:
    """Get scope resolver singleton."""
    global _scope_resolver
    if _scope_resolver is None:
        _scope_resolver = ScopeResolver()
    return _scope_resolver
