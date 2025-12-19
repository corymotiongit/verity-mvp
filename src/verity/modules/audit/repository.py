"""
Verity Audit - Repository.

Database operations for audit events. IMMUTABLE - only INSERT, never UPDATE/DELETE.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client

from verity.core.supabase_client import get_supabase_client


class AuditRepository:
    """
    Repository for audit events.

    IMMUTABLE: Only INSERT operations allowed. Never UPDATE or DELETE.
    """

    def __init__(self, client: Client | None = None):
        self._client = client or get_supabase_client()

    @property
    def table_name(self) -> str:
        return "audit_events"

    @property
    def table(self):
        return self._client.table(self.table_name)

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create an audit event. This is the ONLY write operation allowed.

        Audit events are immutable and cannot be updated or deleted.
        """
        response = self.table.insert(data).execute()
        return response.data[0]

    async def list_timeline(
        self,
        action: str | None = None,
        actor_id: UUID | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, int]:
        """List audit events with optional filters."""
        offset = int(page_token) if page_token else 0

        query = self.table.select("*", count="exact")

        if action:
            query = query.eq("action", action)
        if actor_id:
            query = query.eq("actor_id", str(actor_id))
        if since:
            query = query.gte("timestamp", since.isoformat())
        if until:
            query = query.lte("timestamp", until.isoformat())

        response = (
            query.order("timestamp", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        items = response.data or []
        total = response.count or 0

        next_token = None
        if offset + len(items) < total:
            next_token = str(offset + page_size)

        return items, next_token, total

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all audit events for a specific entity."""
        response = (
            self.table.select("*")
            .eq("entity_type", entity_type)
            .eq("entity_id", str(entity_id))
            .order("timestamp", desc=True)
            .execute()
        )
        return response.data or []

    # NOTE: No update() or delete() methods - audit is immutable
