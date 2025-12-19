"""
Verity Audit - Router.

API endpoints for audit trail. READ-ONLY for admin/auditor roles.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends

from verity.auth import User, get_current_user
from verity.deps import require_audit, require_auditor
from verity.modules.audit.schemas import (
    AuditAction,
    AuditTimelineResponse,
    EntityHistoryResponse,
    EntityType,
)
from verity.modules.audit.service import AuditService

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[require_audit, require_auditor],
)


def get_service() -> AuditService:
    """Get audit service instance."""
    return AuditService()


@router.get("/timeline", response_model=AuditTimelineResponse)
async def get_audit_timeline(
    action: AuditAction | None = None,
    actor_id: UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page_size: int = 50,
    page_token: str | None = None,
    user: User = Depends(get_current_user),
    service: AuditService = Depends(get_service),
):
    """Get audit timeline. Admin/Auditor only."""
    return await service.get_timeline(
        action=action,
        actor_id=actor_id,
        since=since,
        until=until,
        page_size=page_size,
        page_token=page_token,
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=EntityHistoryResponse)
async def get_entity_history(
    entity_type: EntityType,
    entity_id: UUID,
    user: User = Depends(get_current_user),
    service: AuditService = Depends(get_service),
):
    """Get history for a specific entity. Admin/Auditor only."""
    return await service.get_entity_history(entity_type, entity_id)
