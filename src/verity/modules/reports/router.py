"""
Verity Reports - Router.

API endpoints for reports.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from verity.auth import User, get_current_user
from verity.deps import require_admin, require_reports
from verity.modules.reports.schemas import (
    ReportCreateRequest,
    ReportListResponse,
    ReportResponse,
)
from verity.modules.reports.service import ReportsService
from verity.schemas import PaginationMeta

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[require_reports],
)


def get_service() -> ReportsService:
    """Get reports service instance."""
    return ReportsService()


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    request: ReportCreateRequest,
    user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_service),
):
    """Create a new report."""
    return await service.create_report(request, user)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_service),
):
    """Get report by ID."""
    return await service.get_report(report_id)


@router.delete("/{report_id}", status_code=204, dependencies=[require_admin])
async def delete_report(
    report_id: UUID,
    user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_service),
):
    """Delete a report. Admin only."""
    await service.delete_report(report_id)


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page_size: int = 20,
    page_token: str | None = None,
    user: User = Depends(get_current_user),
    service: ReportsService = Depends(get_service),
):
    """List reports."""
    items, next_token, total = await service.list_reports(page_size, page_token)
    return ReportListResponse(
        items=items,
        meta=PaginationMeta(
            total_count=total,
            page_size=page_size,
            next_page_token=next_token,
            has_more=next_token is not None,
        ),
    )
