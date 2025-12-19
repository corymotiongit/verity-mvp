"""
Verity Audit - Service.

Business logic for audit trail. IMMUTABLE timeline.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from verity.auth.schemas import User
from verity.modules.audit.repository import AuditRepository
from verity.modules.audit.schemas import (
    AuditAction,
    AuditEvent,
    AuditTimelineResponse,
    EntityHistoryResponse,
)
from verity.schemas import PaginationMeta


class AuditService:
    """Service for audit operations."""

    def __init__(self, repository: AuditRepository | None = None):
        self.repository = repository or AuditRepository()

    async def log_event(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: UUID,
        actor: User,
        payload: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditEvent:
        """
        Log an audit event. This creates an immutable record.
        """
        event_id = uuid4()

        event_data = {
            "id": str(event_id),
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "actor_id": str(actor.id),
            "actor_email": actor.email,
            "actor_role": (
                "admin" if actor.is_admin else ((actor.roles[0] if actor.roles else "user"))
            ),
            "payload": payload,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        created = await self.repository.create(event_data)
        return self._to_event(created)

    async def get_timeline(
        self,
        action: str | None = None,
        actor_id: UUID | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> AuditTimelineResponse:
        """Get audit timeline with filters."""
        events, next_token, total = await self.repository.list_timeline(
            action=action,
            actor_id=actor_id,
            since=since,
            until=until,
            page_size=page_size,
            page_token=page_token,
        )

        return AuditTimelineResponse(
            events=[self._to_event(e) for e in events],
            meta=PaginationMeta(
                total_count=total,
                page_size=page_size,
                next_page_token=next_token,
                has_more=next_token is not None,
            ),
        )

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> EntityHistoryResponse:
        """Get complete history for an entity."""
        events = await self.repository.get_entity_history(entity_type, entity_id)

        return EntityHistoryResponse(
            entity_type=entity_type,
            entity_id=entity_id,
            current_state=None,  # Could fetch from entity table if needed
            events=[self._to_event(e) for e in events],
        )

    def _to_event(self, data: dict[str, Any]) -> AuditEvent:
        """Convert database record to AuditEvent."""
        return AuditEvent(
            id=UUID(data["id"]),
            action=data["action"],
            entity_type=data["entity_type"],
            entity_id=UUID(data["entity_id"]),
            actor_id=UUID(data["actor_id"]),
            actor_email=data.get("actor_email"),
            actor_role=data.get("actor_role"),
            payload=data.get("payload"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            timestamp=data["timestamp"],
        )
