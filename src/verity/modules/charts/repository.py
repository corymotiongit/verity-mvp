"""
Verity Charts - Repository.

Database operations for saved charts.
"""

from typing import Any
from uuid import UUID

from verity.core.repository import BaseRepository


class ChartsRepository(BaseRepository[dict[str, Any]]):
    """Repository for charts in Supabase."""

    @property
    def table_name(self) -> str:
        return "charts"

    async def list_by_user(
        self,
        user_id: UUID,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List charts created by a specific user."""
        return await self.list(
            page_size=page_size,
            page_token=page_token,
            filters={"created_by": str(user_id)},
        )
