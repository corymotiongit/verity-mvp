"""
Verity Tags - Schemas

Pydantic models for tag management.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Tag Schemas
# =============================================================================

class TagBase(BaseModel):
    """Base tag fields."""
    name: str = Field(..., min_length=1, max_length=50, description="Tag name")
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")


class TagCreate(TagBase):
    """Create a new tag."""
    pass


class TagUpdate(BaseModel):
    """Update an existing tag."""
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(TagBase):
    """Tag response with metadata."""
    id: UUID
    org_id: UUID
    document_count: int = Field(default=0, description="Number of documents with this tag")
    created_by: UUID | None = None
    created_at: datetime


class TagListResponse(BaseModel):
    """List of tags."""
    items: List[TagResponse]
    total: int


# =============================================================================
# Document Tag Assignment Schemas
# =============================================================================

class DocumentTagAssignment(BaseModel):
    """Assign/remove tags from a document."""
    add_tags: List[UUID] = Field(default_factory=list, description="Tag IDs to add")
    remove_tags: List[UUID] = Field(default_factory=list, description="Tag IDs to remove")


class DocumentTagsResponse(BaseModel):
    """Tags assigned to a document."""
    document_id: UUID
    tags: List[TagResponse]


# =============================================================================
# Document Metadata (Extended for Organization)
# =============================================================================

class DocumentCategory(BaseModel):
    """Controlled vocabulary for document types."""
    VALID_CATEGORIES: List[str] = [
        "PDF", "Excel", "Dataset", "Contrato", "Reporte", 
        "Factura", "Poliza", "Observaciones", "Otro"
    ]


class DocumentMetadataExtended(BaseModel):
    """
    Extended metadata for documents with clear organization:
    
    - project (required): Main container/client/case
    - category (required): Controlled type (PDF, Excel, Contrato, etc.)
    - period (optional): Time reference (2024, 2024Q1, 2024-06)
    - source (optional): Origin (SHCP, cliente, interno)
    - tags (optional): Free-form labels
    """
    project: str = Field(..., min_length=1, max_length=100, description="Project name (required)")
    category: str = Field(..., description="Document type from controlled list")
    period: str | None = Field(default=None, max_length=20, description="Time period (e.g., 2024, 2024Q1)")
    source: str | None = Field(default=None, max_length=100, description="Data source (e.g., SHCP, cliente)")
    
    # Tags are managed separately via /documents/{id}/tags endpoint


# =============================================================================
# Collection (Saved Filter) Schemas
# =============================================================================

class CollectionFilter(BaseModel):
    """Filter criteria for a collection."""
    project: str | None = None
    categories: List[str] = Field(default_factory=list)
    tags: List[UUID] = Field(default_factory=list)
    period: str | None = None
    source: str | None = None
    document_ids: List[UUID] | None = None  # Explicit list of docs


class CollectionCreate(BaseModel):
    """Create a saved collection (filter)."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    filter: CollectionFilter


class CollectionUpdate(BaseModel):
    """Update a collection."""
    name: str | None = None
    description: str | None = None
    filter: CollectionFilter | None = None


class CollectionResponse(BaseModel):
    """Collection response with full audit trail."""
    id: UUID
    org_id: UUID
    name: str
    description: str | None = None
    filter: CollectionFilter
    document_count: int = 0  # Computed based on filter
    
    # Audit trail
    created_by: UUID | None = None
    created_at: datetime
    updated_by: UUID | None = None
    updated_at: datetime | None = None
    last_used_at: datetime | None = None  # Track when filter was last applied


class CollectionListResponse(BaseModel):
    """List of collections."""
    items: List[CollectionResponse]
    total: int


# =============================================================================
# Bulk Actions
# =============================================================================

class BulkTagAction(BaseModel):
    """Bulk add/remove tags from multiple documents."""
    document_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    add_tags: List[UUID] = Field(default_factory=list)
    remove_tags: List[UUID] = Field(default_factory=list)


class BulkMoveAction(BaseModel):
    """Move documents to a different project."""
    document_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    new_project: str = Field(..., min_length=1, max_length=100)


class BulkCategoryAction(BaseModel):
    """Change category for multiple documents."""
    document_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    new_category: str


class BulkActionResult(BaseModel):
    """Result of a bulk action."""
    success_count: int
    failed_count: int
    failed_ids: List[UUID] = Field(default_factory=list)
    message: str
