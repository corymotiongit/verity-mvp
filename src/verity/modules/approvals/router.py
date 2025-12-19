"""
Verity Approvals - Router.

API endpoints for approval operations.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from verity.auth import User, get_current_user
from verity.deps import require_approvals, require_approver
from verity.modules.approvals.schemas import (
    ApprovalCreateRequest,
    ApprovalDetailResponse,
    ApprovalListResponse,
    ApprovalResponse,
    ApprovalStatus,
    FieldApproval,
    FieldApprovalUpdate,
)
from verity.modules.approvals.service import ApprovalsService
from verity.schemas import PaginationMeta

router = APIRouter(
    prefix="/approvals",
    tags=["approvals"],
    dependencies=[require_approvals],
)


def get_service() -> ApprovalsService:
    """Get approvals service instance."""
    return ApprovalsService()


@router.post("", response_model=ApprovalResponse, status_code=201)
async def create_approval(
    request: ApprovalCreateRequest,
    user: User = Depends(get_current_user),
    service: ApprovalsService = Depends(get_service),
):
    """Create a new approval request."""
    return await service.create_approval(request, user)


@router.get("/pending", response_model=ApprovalListResponse)
async def list_pending_approvals(
    page_size: int = 20,
    page_token: str | None = None,
    user: User = Depends(get_current_user),
    service: ApprovalsService = Depends(get_service),
):
    """List pending approvals."""
    items, next_token, total = await service.list_pending(page_size, page_token)
    return ApprovalListResponse(
        items=items,
        meta=PaginationMeta(
            total_count=total,
            page_size=page_size,
            next_page_token=next_token,
            has_more=next_token is not None,
        ),
    )


@router.get("", response_model=ApprovalListResponse)
async def list_approvals(
    status: ApprovalStatus | None = None,
    page_size: int = 20,
    page_token: str | None = None,
    user: User = Depends(get_current_user),
    service: ApprovalsService = Depends(get_service),
):
    """List all approvals with optional status filter."""
    items, next_token, total = await service.list_approvals(
        status=status,
        page_size=page_size,
        page_token=page_token,
    )
    return ApprovalListResponse(
        items=items,
        meta=PaginationMeta(
            total_count=total,
            page_size=page_size,
            next_page_token=next_token,
            has_more=next_token is not None,
        ),
    )


@router.get("/{approval_id}", response_model=ApprovalDetailResponse)
async def get_approval(
    approval_id: UUID,
    user: User = Depends(get_current_user),
    service: ApprovalsService = Depends(get_service),
):
    """Get approval with diff."""
    return await service.get_approval_detail(approval_id)


@router.patch(
    "/{approval_id}/fields/{field_name}",
    response_model=FieldApproval,
    dependencies=[require_approver],
)
async def update_field_approval(
    approval_id: UUID,
    field_name: str,
    update: FieldApprovalUpdate,
    user: User = Depends(get_current_user),
    service: ApprovalsService = Depends(get_service),
):
    """Approve or reject a specific field. Requires approver or admin role."""
    return await service.update_field_approval(approval_id, field_name, update, user)
