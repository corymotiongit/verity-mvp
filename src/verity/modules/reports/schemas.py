"""
Verity Reports - Schemas.

Pydantic models for report operations.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from verity.schemas import PaginationMeta


ReportType = Literal["summary", "detailed", "executive", "custom"]
ReportStatus = Literal["pending", "generating", "ready", "failed"]


class ScheduleConfig(BaseModel):
    """Report schedule configuration."""

    frequency: Literal["once", "daily", "weekly", "monthly"]
    next_run: datetime | None = None


class ReportCreateRequest(BaseModel):
    """Request to create a report."""

    title: str = Field(..., min_length=1, max_length=200)
    type: ReportType
    parameters: dict[str, Any] | None = None
    schedule: ScheduleConfig | None = None


class ReportResponse(BaseModel):
    """Report response."""

    id: UUID
    title: str
    type: ReportType
    status: ReportStatus
    content: dict[str, Any] | None = None
    download_url: str | None = None
    parameters: dict[str, Any] | None = None
    created_at: datetime
    created_by: UUID
    completed_at: datetime | None = None


class ReportListResponse(BaseModel):
    """Paginated list of reports."""

    items: list[ReportResponse]
    meta: PaginationMeta
