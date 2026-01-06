"""
Verity Upload v2 - Schemas.

Pydantic models for generic file upload endpoint.
Part of PR1: Upload + Storage + Metadata.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TableInfo(BaseModel):
    """Basic table information returned after upload."""
    
    table_id: str = Field(..., description="Unique table identifier (hash-based)")
    table_name: str = Field(..., description="Friendly name for the table")
    file_type: str = Field(..., description="Detected file type (csv, excel, pdf, text, unknown)")
    row_count: int = Field(ge=0, description="Number of rows (excludes header for CSV)")


class UploadMetadata(BaseModel):
    """Detailed metadata about the uploaded file."""
    
    filename: str = Field(..., description="Original filename")
    original_name: str = Field(..., description="Original filename (alias)")
    mime_type: str = Field(..., description="MIME type from upload")
    file_type: str = Field(..., description="Detected file type")
    size_bytes: int = Field(ge=0, description="File size in bytes")
    row_count: int = Field(ge=0, description="Row count (0 if not applicable)")
    storage_path: str = Field(..., description="Relative path in uploads/ directory")
    conversation_id: str = Field(..., description="Conversation scope for this upload")
    created_at: datetime = Field(..., description="Upload timestamp (UTC)")
    created_by: UUID = Field(..., description="User ID who uploaded")


class UploadResponse(BaseModel):
    """Response from file upload endpoint."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    table_id: str = Field(..., description="Unique table identifier")
    table_info: TableInfo = Field(..., description="Basic table information")
    metadata: UploadMetadata = Field(..., description="Detailed file metadata")
    
    # Schema inference (PR2 will populate this)
    inference_status: str = Field(
        default="pending",
        description="Schema inference status (pending, completed, failed)",
    )
    inferred_schema: dict | None = Field(
        default=None,
        description="Inferred schema from DIA",
        alias="schema",
        serialization_alias="schema",
    )
    
    # Warnings/errors
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-critical warnings (e.g., 'High % of nulls in column X')",
    )
    
    message: str = Field(
        default="File uploaded successfully",
        description="Human-readable status message",
    )


class UploadListResponse(BaseModel):
    """List of uploaded files in a conversation."""
    
    conversation_id: str
    tables: list[TableInfo]
    total_count: int = Field(ge=0)
