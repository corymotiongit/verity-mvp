"""
Verity Reports - Service.

Business logic for report generation.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from verity.auth.schemas import User
from verity.modules.reports.repository import ReportsRepository
from verity.modules.reports.schemas import (
    ReportCreateRequest,
    ReportResponse,
)


class ReportsService:
    """Service for report operations."""

    def __init__(self, repository: ReportsRepository | None = None):
        self.repository = repository or ReportsRepository()

    async def create_report(
        self,
        request: ReportCreateRequest,
        user: User,
    ) -> ReportResponse:
        """Create a new report."""
        report_id = uuid4()

        report_data = {
            "id": str(report_id),
            "title": request.title,
            "type": request.type,
            "status": "pending",
            "parameters": request.parameters or {},
            "schedule": request.schedule.model_dump() if request.schedule else None,
            "created_by": str(user.id),
        }

        created = await self.repository.create(report_data)

        # In production, queue report generation here
        # For now, mark as ready with placeholder content
        await self.repository.update_status(
            report_id,
            status="ready",
            content={"summary": "Report generated successfully"},
        )

        return await self.get_report(report_id)

    async def get_report(self, report_id: UUID) -> ReportResponse:
        """Get report by ID."""
        report = await self.repository.get_by_id_or_raise(report_id)
        return self._to_response(report)

    async def delete_report(self, report_id: UUID) -> None:
        """Delete a report."""
        await self.repository.delete(report_id)

    async def list_reports(
        self,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[ReportResponse], str | None, int]:
        """List reports."""
        items, next_token = await self.repository.list(
            page_size=page_size,
            page_token=page_token,
        )

        reports = [self._to_response(r) for r in items]
        return reports, next_token, len(items)

    def _to_response(self, data: dict[str, Any]) -> ReportResponse:
        """Convert database record to response."""
        return ReportResponse(
            id=UUID(data["id"]),
            title=data["title"],
            type=data["type"],
            status=data["status"],
            content=data.get("content"),
            download_url=data.get("download_url"),
            parameters=data.get("parameters"),
            created_at=data["created_at"],
            created_by=UUID(data["created_by"]),
            completed_at=data.get("completed_at"),
        )
