"""
Verity Audit - Schemas.

Pydantic models for audit operations.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from verity.schemas import PaginationMeta


AuditAction = Literal["create", "update", "delete", "approve", "reject", "login", "logout"]
EntityType = Literal["document", "approval", "report", "chart", "forecast", "conversation"]


class AuditEvent(BaseModel):
    """Single audit event (immutable)."""

    id: UUID
    action: AuditAction
    entity_type: str
    entity_id: UUID
    actor_id: UUID
    actor_email: EmailStr | None = None
    actor_role: str | None = None
    payload: dict[str, Any] | None = Field(
        default=None, description="Snapshot of changes made"
    )
    ip_address: str | None = None
    user_agent: str | None = None
    timestamp: datetime


class AuditTimelineResponse(BaseModel):
    """Paginated audit timeline."""

    events: list[AuditEvent]
    meta: PaginationMeta


class EntityHistoryResponse(BaseModel):
    """History of a specific entity."""

    entity_type: str
    entity_id: UUID
    current_state: dict[str, Any] | None = None
    events: list[AuditEvent]
