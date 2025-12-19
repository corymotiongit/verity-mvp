"""
Verity Documents - Service.

Business logic for document operations with Gemini File Search Tool.
Supports multi-organization with isolated File Search stores.
"""

import hashlib
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID, uuid4

from verity.auth.schemas import User
from verity.core.gemini import (
    create_file_search_store,
    search_in_store,
    upload_to_file_search_store,
    get_or_create_file_search_store,
    search_with_file_search,
)
from verity.exceptions import ExternalServiceException, NotFoundException
from verity.modules.documents.schemas import (
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    SearchResult,
)

logger = logging.getLogger(__name__)

# Persistence file paths
DOCUMENTS_DB_PATH = Path("uploads/documents_db.json")
ORG_STORES_DB_PATH = Path("uploads/org_stores_db.json")

def _load_json_db(path: Path) -> dict:
    """Load JSON database from file."""
    if path.exists():
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load {path}: {e}")
    return {}

def _save_json_db(path: Path, data: dict):
    """Save JSON database to file."""
    try:
        import json
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save {path}: {e}")

# Load persisted data on module import
_documents: dict[str, dict[str, Any]] = _load_json_db(DOCUMENTS_DB_PATH)
_org_stores: dict[str, str] = _load_json_db(ORG_STORES_DB_PATH)

logger.info(f"Loaded {len(_documents)} documents and {len(_org_stores)} org stores from disk")


class DocumentsService:
    """Service for document operations."""
    
    @property
    def _documents(self) -> dict[str, dict[str, Any]]:
        """Access to in-memory documents store."""
        return _documents

    def _get_org_store(self, user: User, project: str | None = None) -> str:
        """
        Get or create File Search store for user's organization.
        
        If project is specified, creates a separate store for that project.
        This enables real API-level filtering by project.
        """
        org_id = str(user.org_id)
        
        # Build store key - org_id or org_id:project
        store_key = f"{org_id}:{project}" if project else org_id
        
        # Check in-memory cache
        if store_key in _org_stores:
            return _org_stores[store_key]
        
        # Check if org has a default store (from DB/org object)
        if not project and user.organization and user.organization.file_search_store_id:
            store_name = user.organization.file_search_store_id
            _org_stores[store_key] = store_name
            _save_json_db(ORG_STORES_DB_PATH, _org_stores)
            return store_name
        
        # Create new store for org/project
        org_name = user.organization.name if user.organization else "default"
        store_display_name = f"{org_name} - {project}" if project else org_name
        store_name = create_file_search_store(user.org_id, store_display_name)
        _org_stores[store_key] = store_name
        _save_json_db(ORG_STORES_DB_PATH, _org_stores)
        
        logger.info(f"Created new store: {store_name} for project: {project or 'default'}")
        
        return store_name
    
    def get_project_stores(self, user: User) -> dict[str, str]:
        """Get all project stores for an organization."""
        org_id = str(user.org_id)
        stores = {}
        for key, store_name in _org_stores.items():
            if key.startswith(org_id):
                project = key.split(":", 1)[1] if ":" in key else "default"
                stores[project] = store_name
        return stores

    async def ingest_document(
        self,
        file: BinaryIO,
        filename: str,
        mime_type: str,
        display_name: str | None,
        metadata: dict | None,
        user: User,
    ) -> DocumentResponse:
        """
        Ingest a document into the organization's File Search store.
        
        For tabular files (CSV/Excel):
        1. Save raw file (original preserved)
        2. Normalize to canonical format (UTF-8, clean headers, etc.)
        3. Save audit log of transformations
        
        Isolation: Documents are uploaded to org-specific store.
        """
        from verity.modules.data.normalizer import get_file_normalizer
        
        doc_id = uuid4()
        final_display_name = display_name or filename
        tmp_path = None
        canonical_path = None
        normalization_audit = None

        logger.info(
            f"Ingesting document: filename={filename}, "
            f"org_id={user.org_id}, user_id={user.id}"
        )

        try:
            # Read file content
            content = file.read()
            size_bytes = len(content)
            content_hash = hashlib.sha256(content).hexdigest()

            # Save to temp file for processing
            suffix = Path(filename).suffix or ".bin"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # Check if tabular file (needs normalization)
            is_tabular = suffix.lower() in [".csv", ".xlsx", ".xls"]
            
            if is_tabular:
                # Use FileNormalizer pipeline
                normalizer = get_file_normalizer()
                canonical_path, normalization_audit = normalizer.normalize(
                    doc_id=str(doc_id),
                    source_path=Path(tmp_path),
                    original_filename=filename
                )
                local_path = canonical_path
                logger.info(
                    f"Normalized tabular file: {normalization_audit.rows_before} → "
                    f"{normalization_audit.rows_after} rows, "
                    f"{len(normalization_audit.transforms_applied)} transforms"
                )
            else:
                # Non-tabular: save directly to uploads
                uploads_dir = Path("uploads")
                uploads_dir.mkdir(exist_ok=True)
                local_filename = f"{doc_id}_{filename}"
                local_path = uploads_dir / local_filename
                with open(local_path, "wb") as f:
                    f.write(content)
                logger.info(f"Saved non-tabular file: {local_path}")

            # Get org's File Search store - use project-specific store if specified
            project = metadata.get("project") if metadata else None
            store_name = self._get_org_store(user, project=project)

            # CRITICAL: Only index non-tabular files in File Search
            # CSV/Excel should NOT go to File Search (prevents DocQA from answering data queries)
            upload_result = {"status": "ready"}  # Default for tabular files
            
            if not is_tabular:
                # Upload to File Search store for PDF/text documents
                upload_result = upload_to_file_search_store(
                    file_path=tmp_path,
                    display_name=final_display_name,
                    store_name=store_name,
                    metadata=metadata,
                )
                logger.info(f"[FILE_SEARCH] Indexed non-tabular file: {final_display_name}")
            else:
                logger.info(f"[FILE_SEARCH] SKIPPED tabular file (CSV/Excel only uses DataEngine): {final_display_name}")

            # Build document metadata
            now = datetime.now(timezone.utc)
            doc_data = {
                "id": str(doc_id),
                "org_id": str(user.org_id),
                "display_name": final_display_name,
                "filename": filename,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "content_hash": content_hash,
                "store_name": store_name,
                "gemini_file_name": final_display_name,  # Reference in store
                "status": upload_result.get("status", "ready"),
                "metadata": metadata or {},
                "created_by": str(user.id),
                "created_at": now.isoformat(),
                "local_path": str(local_path),  # Canonical file path for data queries
            }
            
            # Add normalization info for tabular files
            if normalization_audit:
                doc_data["normalization"] = {
                    "raw_path": normalization_audit.raw_file,
                    "canonical_path": normalization_audit.canonical_file,
                    "rows_before": normalization_audit.rows_before,
                    "rows_after": normalization_audit.rows_after,
                    "transforms_count": len(normalization_audit.transforms_applied),
                    "skipped": normalization_audit.skipped,
                }

            # Store in memory (replace with DB in production)
            _documents[str(doc_id)] = doc_data
            _save_json_db(DOCUMENTS_DB_PATH, _documents)

            logger.info(f"Document ingested: id={doc_id}, store={store_name}")

            return DocumentResponse(
                id=doc_id,
                display_name=final_display_name,
                mime_type=mime_type,
                size_bytes=size_bytes,
                status=doc_data["status"],
                gemini_uri=store_name,
                gemini_name=final_display_name,
                metadata=metadata,
                created_at=now,
                created_by=user.id,
            )

        except ExternalServiceException:
            raise
        except Exception as e:
            logger.exception(f"Failed to ingest document: {e}")
            raise ExternalServiceException("Document Ingestion", str(e))
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

    async def get_document(self, document_id: UUID, user: User | None = None) -> DocumentResponse:
        """Get document metadata by ID."""
        doc_id_str = str(document_id)
        
        if doc_id_str not in _documents:
            raise NotFoundException("document", document_id)
        
        doc = _documents[doc_id_str]
        
        # Org isolation check
        if user and doc.get("org_id") != str(user.org_id):
            raise NotFoundException("document", document_id)
        
        return self._to_response(doc)

    async def delete_document(self, document_id: UUID, user: User) -> None:
        """Delete a document from local storage AND from File Search store."""
        from verity.core.gemini import delete_document_from_store, list_documents_in_store
        
        doc_id_str = str(document_id)
        
        if doc_id_str not in _documents:
            raise NotFoundException("document", document_id)
        
        doc = _documents[doc_id_str]
        
        # Org isolation check
        if doc.get("org_id") != str(user.org_id):
            raise NotFoundException("document", document_id)
        
        # Try to delete from File Search store
        store_name = doc.get("store_name")
        display_name = doc.get("display_name")
        
        if store_name and display_name:
            try:
                # Find the document in the store by display_name
                store_docs = list_documents_in_store(store_name)
                for store_doc in store_docs:
                    if store_doc.get("display_name") == display_name:
                        delete_document_from_store(store_doc["name"])
                        logger.info(f"Deleted from File Search store: {store_doc['name']}")
                        break
            except Exception as e:
                logger.warning(f"Failed to delete from File Search store: {e}")
                # Continue with local deletion even if store deletion fails
        
        # Delete local file copy
        local_path = doc.get("local_path")
        if local_path:
            try:
                Path(local_path).unlink(missing_ok=True)
                logger.info(f"Deleted local file: {local_path}")
            except Exception as e:
                logger.warning(f"Failed to delete local file: {e}")
        
        # Delete from local storage
        del _documents[doc_id_str]
        _save_json_db(DOCUMENTS_DB_PATH, _documents)
        logger.info(f"Document deleted: {document_id}")

    def _restore_from_disk(self):
        """Restore document metadata from uploads directory (MVP persistence)."""
        if _documents: return
        
        uploads_dir = Path("uploads")
        if not uploads_dir.exists(): return
        
        logger.info("Restoring documents from disk...")
        for p in uploads_dir.glob("*"):
            try:
                # Expect format: uuid_filename
                parts = p.name.split("_", 1)
                if len(parts) != 2: continue
                
                doc_id = parts[0]
                filename = parts[1]
                
                # Guess mime type
                mime_type = "application/octet-stream"
                if filename.endswith(".csv"): mime_type = "text/csv"
                elif filename.endswith(".pdf"): mime_type = "application/pdf"
                elif filename.endswith(".xlsx"): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                
                # Reconstruct generic metadata
                _documents[doc_id] = {
                    "id": doc_id,
                    "display_name": filename,
                    "filename": filename,
                    "mime_type": mime_type,
                    "size_bytes": p.stat().st_size,
                    "status": "ready",
                    "store_name": "unknown_store", # Lost mapping
                    "org_id": "00000000-0000-0000-0000-000000000100", # Default Test Org
                    "created_at": datetime.fromtimestamp(p.stat().st_ctime, tz=timezone.utc).isoformat(),
                    "created_by": "00000000-0000-0000-0000-000000000001",
                    "metadata": {},
                    "local_path": str(p)
                }
                logger.info(f"Restored document: {filename} ({doc_id})")
            except Exception as e:
                logger.warning(f"Failed to restore {p}: {e}")

    async def list_documents(
        self,
        user: User,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[DocumentResponse], str | None, int]:
        """List documents for user's organization."""
        # Restore from disk if empty (MVP persistence)
        self._restore_from_disk()
        
        # Filter by org_id
        org_docs = [
            d for d in _documents.values()
            if d.get("org_id") == str(user.org_id)
        ]
        
        # Sort by created_at descending
        org_docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Pagination
        offset = int(page_token) if page_token else 0
        docs = org_docs[offset : offset + page_size]
        
        next_token = None
        if offset + len(docs) < len(org_docs):
            next_token = str(offset + page_size)
        
        responses = []
        for d in docs:
            try:
                responses.append(self._to_response(d))
            except Exception as e:
                logger.error(f"Skipping corrupt document {d.get('id')}: {e}")
                
        return responses, next_token, len(org_docs)

    async def search_documents(
        self,
        request: DocumentSearchRequest,
        user: User,
        request_id: UUID,
    ) -> DocumentSearchResponse:
        """
        Search documents in user's organization using File Search.
        
        Isolation: Searches only in org's File Search store.
        """
        logger.info(
            f"Searching documents: query='{request.query}', "
            f"org_id={user.org_id}, request_id={request_id}"
        )

        # Get org's store
        store_name = self._get_org_store(user)
        
        # Get org's documents for result mapping
        org_docs = [
            d for d in _documents.values()
            if d.get("org_id") == str(user.org_id)
        ]

        if not org_docs:
            return DocumentSearchResponse(results=[], request_id=request_id)

        try:
            # Build search prompt
            search_prompt = f"""Search the documents and find information relevant to:

Query: {request.query}

Provide a detailed answer with specific references to source documents."""

            # Search in org's store only
            search_result = search_in_store(
                query=search_prompt,
                store_name=store_name,
            )

            # Build results
            results = []
            if search_result.get("text"):
                for doc in org_docs[:request.max_results]:
                    results.append(
                        SearchResult(
                            document_id=UUID(doc["id"]),
                            document_name=doc["display_name"],
                            snippet=search_result["text"][:200],
                            relevance_score=0.9,
                        )
                    )

            logger.info(f"Search completed: {len(results)} results")
            return DocumentSearchResponse(
                results=results[:request.max_results],
                request_id=request_id,
            )

        except Exception as e:
            logger.exception(f"Search failed: {e}")
            raise ExternalServiceException("Document Search", str(e))

    def _to_response(self, doc: dict[str, Any]) -> DocumentResponse:
        """Convert document dict to response."""
        return DocumentResponse(
            id=UUID(doc["id"]),
            display_name=doc["display_name"],
            mime_type=doc["mime_type"],
            size_bytes=doc.get("size_bytes"),
            status=doc.get("status", "ready"),
            gemini_uri=doc.get("store_name"),
            gemini_name=doc.get("gemini_file_name"),
            metadata=doc.get("metadata"),
            created_at=doc.get("created_at"),
            created_by=UUID(doc["created_by"]) if doc.get("created_by") else None,
        )

# Force reload
