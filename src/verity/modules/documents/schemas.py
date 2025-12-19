"""
Verity Documents - Schemas.

Pydantic models for document operations.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from verity.schemas import PaginationMeta


# =============================================================================
# Request Schemas
# =============================================================================


class DocumentSearchRequest(BaseModel):
    """Request for document search."""

    query: str = Field(..., min_length=1, max_length=1000)
    document_ids: list[UUID] | None = Field(
        default=None, description="Limit search to specific documents"
    )
    max_results: int = Field(default=5, ge=1, le=20)


# =============================================================================
# Response Schemas
# =============================================================================


class DocumentResponse(BaseModel):
    """Document metadata response with organization structure."""

    id: UUID
    display_name: str
    gemini_uri: str = Field(..., description="Gemini File API URI")
    mime_type: str
    size_bytes: int
    status: Literal["processing", "ready", "failed"]
    
    # Organization structure (clear hierarchy)
    project: str | None = Field(default=None, description="Project name (required for new uploads)")
    category: str | None = Field(default=None, description="Document type: PDF, Excel, Contrato, etc.")
    period: str | None = Field(default=None, description="Time period: 2024, 2024Q1")
    source: str | None = Field(default=None, description="Data source: SHCP, cliente")
    tags: list[str] = Field(default_factory=list, description="Tag names assigned to document")
    
    # Legacy metadata (for backwards compatibility)
    metadata: dict[str, Any] | None = None
    created_at: datetime
    created_by: UUID


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    items: list[DocumentResponse]
    meta: PaginationMeta


class SearchResult(BaseModel):
    """Single search result."""

    document_id: UUID
    document_name: str
    snippet: str
    relevance_score: float = Field(ge=0, le=1)


class DocumentSearchResponse(BaseModel):
    """Document search response."""

    results: list[SearchResult]
    request_id: UUID
