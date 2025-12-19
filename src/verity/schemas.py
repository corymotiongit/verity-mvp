"""
Verity - Common Schemas.

Shared Pydantic models used across all modules.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


# =============================================================================
# Error Responses
# =============================================================================


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional context")
    request_id: UUID | None = Field(default=None, description="Request ID for tracing")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail


# =============================================================================
# Pagination
# =============================================================================


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total_count: int = Field(ge=0)
    page_size: int = Field(ge=1, le=100)
    next_page_token: str | None = None
    has_more: bool = False


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    meta: PaginationMeta


# =============================================================================
# Common Fields
# =============================================================================


class TimestampMixin(BaseModel):
    """Mixin for created/updated timestamps."""

    created_at: datetime
    updated_at: datetime | None = None


class AuditMixin(TimestampMixin):
    """Mixin for audit fields."""

    created_by: UUID
    updated_by: UUID | None = None


# =============================================================================
# Health Check
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., pattern="^(healthy|degraded)$")
    version: str
    features: dict[str, bool]
    app_env: str | None = None
    is_production: bool | None = None
    agent_row_ids_guard_effective: bool | None = None
