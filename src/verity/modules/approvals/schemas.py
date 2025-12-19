"""
Verity Approvals - Schemas.

Pydantic models for approval operations with field-level granularity.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from verity.schemas import PaginationMeta


ApprovalStatus = Literal["pending", "approved", "rejected", "partial"]


# =============================================================================
# Field Approval
# =============================================================================


class FieldApproval(BaseModel):
    """Individual field approval status."""

    field_name: str
    original_value: Any
    proposed_value: Any
    status: ApprovalStatus = "pending"
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    comment: str | None = None


class FieldApprovalUpdate(BaseModel):
    """Request to update a field's approval status."""

    status: Literal["approved", "rejected"]
    comment: str | None = Field(default=None, max_length=500)


# =============================================================================
# Request Schemas
# =============================================================================


class FieldCreateRequest(BaseModel):
    """Single field in approval request."""

    field_name: str
    original_value: Any
    proposed_value: Any


class ApprovalCreateRequest(BaseModel):
    """Request to create an approval."""

    entity_type: str
    entity_id: UUID
    fields: list[FieldCreateRequest] = Field(..., min_length=1)
    reason: str | None = None
    priority: Literal["low", "normal", "high", "urgent"] = "normal"


# =============================================================================
# Response Schemas
# =============================================================================


class ApprovalResponse(BaseModel):
    """Approval response with field statuses."""

    id: UUID
    entity_type: str
    entity_id: UUID
    status: ApprovalStatus
    fields: list[FieldApproval]
    reason: str | None = None
    priority: str
    created_at: datetime
    created_by: UUID
    updated_at: datetime | None = None


class FieldDiff(BaseModel):
    """Diff representation for a field."""

    before: Any
    after: Any
    diff_html: str | None = None


class ApprovalDetailResponse(ApprovalResponse):
    """Detailed approval with diff."""

    diff: dict[str, FieldDiff] | None = None


class ApprovalListResponse(BaseModel):
    """Paginated list of approvals."""

    items: list[ApprovalResponse]
    meta: PaginationMeta
