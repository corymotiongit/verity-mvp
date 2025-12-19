"""
Verity Reports - Repository.

Database operations for reports.
"""

from typing import Any
from uuid import UUID

from verity.core.repository import BaseRepository


class ReportsRepository(BaseRepository[dict[str, Any]]):
    """Repository for reports in Supabase."""

    @property
    def table_name(self) -> str:
        return "reports"

    async def list_by_user(
        self,
        user_id: UUID,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List reports created by a specific user."""
        return await self.list(
            page_size=page_size,
            page_token=page_token,
            filters={"created_by": str(user_id)},
        )

    async def update_status(
        self,
        report_id: UUID,
        status: str,
        content: dict | None = None,
        download_url: str | None = None,
    ) -> dict[str, Any]:
        """Update report status and content."""
        data = {"status": status}
        if content is not None:
            data["content"] = content
        if download_url is not None:
            data["download_url"] = download_url
        return await self.update(report_id, data)
