"""
Verity Charts - Schemas.

Pydantic models for chart operations.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from verity.schemas import PaginationMeta


ChartType = Literal["bar", "line", "pie", "scatter", "area", "auto"]
ChartFormat = Literal["vega-lite", "chartjs"]


# =============================================================================
# Request Schemas
# =============================================================================


class ChartGenerateRequest(BaseModel):
    """Request to generate a chart spec."""

    data: list[dict[str, Any]] = Field(..., min_length=1)
    chart_type: ChartType = "auto"
    title: str | None = None
    format: ChartFormat = "vega-lite"
    save: bool = Field(
        default=False,
        description="If true, persist the chart_spec to database",
    )


# =============================================================================
# Response Schemas
# =============================================================================


class ChartGenerateResponse(BaseModel):
    """Generated chart spec (not saved by default)."""

    spec: dict[str, Any]
    format: ChartFormat
    saved: bool = False


class ChartResponse(BaseModel):
    """Saved chart response."""

    id: UUID
    title: str | None = None
    spec: dict[str, Any]
    format: ChartFormat
    created_at: datetime
    created_by: UUID


class ChartListResponse(BaseModel):
    """Paginated list of saved charts."""

    items: list[ChartResponse]
    meta: PaginationMeta
