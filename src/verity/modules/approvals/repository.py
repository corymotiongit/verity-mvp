"""
Verity Approvals - Repository.

Database operations for approvals.
"""

from typing import Any
from uuid import UUID

from verity.core.repository import BaseRepository


class ApprovalsRepository(BaseRepository[dict[str, Any]]):
    """Repository for approvals in Supabase."""

    @property
    def table_name(self) -> str:
        return "approvals"

    async def list_pending(
        self,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List pending approvals."""
        offset = int(page_token) if page_token else 0

        response = (
            self.table.select("*", count="exact")
            .eq("status", "pending")
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        items = response.data or []
        total = response.count or 0

        next_token = None
        if offset + len(items) < total:
            next_token = str(offset + page_size)

        return items, next_token

    async def list_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[dict[str, Any]]:
        """List all approvals for a specific entity."""
        response = (
            self.table.select("*")
            .eq("entity_type", entity_type)
            .eq("entity_id", str(entity_id))
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []

    async def update_field(
        self,
        approval_id: UUID,
        field_name: str,
        field_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update a specific field in an approval.

        Uses Postgres JSONB operations to update the field.
        """
        # First get the current approval
        approval = await self.get_by_id_or_raise(approval_id)
        fields = approval.get("fields", [])

        # Update the specific field
        for field in fields:
            if field.get("field_name") == field_name:
                field.update(field_data)
                break

        # Recalculate overall status
        statuses = [f.get("status") for f in fields]
        if all(s == "approved" for s in statuses):
            overall_status = "approved"
        elif all(s == "rejected" for s in statuses):
            overall_status = "rejected"
        elif any(s == "pending" for s in statuses):
            if any(s in ("approved", "rejected") for s in statuses):
                overall_status = "partial"
            else:
                overall_status = "pending"
        else:
            overall_status = "partial"

        # Update the approval
        return await self.update(
            approval_id,
            {"fields": fields, "status": overall_status},
        )
