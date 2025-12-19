"""
Verity Documents - Repository.

Database operations for document metadata.
"""

from typing import Any
from uuid import UUID

from verity.core.repository import BaseRepository


class DocumentsRepository(BaseRepository[dict[str, Any]]):
    """Repository for document metadata in Supabase."""

    @property
    def table_name(self) -> str:
        return "documents"

    async def get_by_gemini_uri(self, gemini_uri: str) -> dict[str, Any] | None:
        """Get document by Gemini URI."""
        response = (
            self.table.select("*")
            .eq("gemini_uri", gemini_uri)
            .maybe_single()
            .execute()
        )
        return response.data

    async def list_by_user(
        self,
        user_id: UUID,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List documents created by a specific user."""
        return await self.list(
            page_size=page_size,
            page_token=page_token,
            filters={"created_by": str(user_id)},
        )

    async def update_status(
        self, id: UUID, status: str, error_message: str | None = None
    ) -> dict[str, Any]:
        """Update document processing status."""
        data = {"status": status}
        if error_message:
            data["error_message"] = error_message
        return await self.update(id, data)
