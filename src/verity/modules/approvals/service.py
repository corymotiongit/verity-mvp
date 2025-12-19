"""
Verity Approvals - Service.

Business logic for approval workflows with field-level granularity.
"""

from datetime import datetime, timezone
from difflib import unified_diff
from typing import Any
from uuid import UUID, uuid4

from verity.auth.schemas import User
from verity.exceptions import ConflictException, NotFoundException
from verity.modules.approvals.repository import ApprovalsRepository
from verity.modules.approvals.schemas import (
    ApprovalCreateRequest,
    ApprovalDetailResponse,
    ApprovalResponse,
    FieldApproval,
    FieldApprovalUpdate,
    FieldDiff,
)


class ApprovalsService:
    """Service for approval operations."""

    def __init__(self, repository: ApprovalsRepository | None = None):
        self.repository = repository or ApprovalsRepository()

    async def create_approval(
        self,
        request: ApprovalCreateRequest,
        user: User,
    ) -> ApprovalResponse:
        """Create a new approval request."""
        approval_id = uuid4()

        fields = [
            {
                "field_name": f.field_name,
                "original_value": f.original_value,
                "proposed_value": f.proposed_value,
                "status": "pending",
                "approved_by": None,
                "approved_at": None,
                "comment": None,
            }
            for f in request.fields
        ]

        approval_data = {
            "id": str(approval_id),
            "entity_type": request.entity_type,
            "entity_id": str(request.entity_id),
            "status": "pending",
            "fields": fields,
            "reason": request.reason,
            "priority": request.priority,
            "created_by": str(user.id),
        }

        created = await self.repository.create(approval_data)
        return self._to_response(created)

    async def get_approval(self, approval_id: UUID) -> ApprovalResponse:
        """Get approval by ID."""
        approval = await self.repository.get_by_id_or_raise(approval_id)
        return self._to_response(approval)

    async def get_approval_detail(self, approval_id: UUID) -> ApprovalDetailResponse:
        """Get approval with diff."""
        approval = await self.repository.get_by_id_or_raise(approval_id)
        response = self._to_response(approval)

        # Generate diffs for each field
        diffs = {}
        for field in approval.get("fields", []):
            field_name = field.get("field_name")
            original = field.get("original_value")
            proposed = field.get("proposed_value")

            diff_html = self._generate_diff(original, proposed)
            diffs[field_name] = FieldDiff(
                before=original,
                after=proposed,
                diff_html=diff_html,
            )

        return ApprovalDetailResponse(
            **response.model_dump(),
            diff=diffs,
        )

    async def update_field_approval(
        self,
        approval_id: UUID,
        field_name: str,
        update: FieldApprovalUpdate,
        user: User,
    ) -> FieldApproval:
        """Approve or reject a specific field."""
        approval = await self.repository.get_by_id_or_raise(approval_id)

        # Find the field
        fields = approval.get("fields", [])
        target_field = None
        for field in fields:
            if field.get("field_name") == field_name:
                target_field = field
                break

        if not target_field:
            raise NotFoundException("field", field_name)

        # Check if already decided
        if target_field.get("status") in ("approved", "rejected"):
            raise ConflictException(
                f"Field '{field_name}' already has status '{target_field.get('status')}'",
                current_state=target_field.get("status"),
                target_state=update.status,
            )

        # Update the field
        now = datetime.now(timezone.utc)
        field_update = {
            "status": update.status,
            "approved_by": str(user.id),
            "approved_at": now.isoformat(),
            "comment": update.comment,
        }

        updated = await self.repository.update_field(
            approval_id, field_name, field_update
        )

        # Find and return the updated field
        for field in updated.get("fields", []):
            if field.get("field_name") == field_name:
                return FieldApproval(**field)

        raise NotFoundException("field", field_name)

    async def list_approvals(
        self,
        status: str | None = None,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[ApprovalResponse], str | None, int]:
        """List approvals with optional status filter."""
        filters = {"status": status} if status else None
        items, next_token = await self.repository.list(
            page_size=page_size,
            page_token=page_token,
            filters=filters,
        )

        responses = [self._to_response(item) for item in items]
        return responses, next_token, len(items)

    async def list_pending(
        self,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[ApprovalResponse], str | None, int]:
        """List pending approvals."""
        items, next_token = await self.repository.list_pending(
            page_size=page_size,
            page_token=page_token,
        )

        responses = [self._to_response(item) for item in items]
        return responses, next_token, len(items)

    def _to_response(self, data: dict[str, Any]) -> ApprovalResponse:
        """Convert database record to response schema."""
        fields = [FieldApproval(**f) for f in data.get("fields", [])]
        return ApprovalResponse(
            id=UUID(data["id"]),
            entity_type=data["entity_type"],
            entity_id=UUID(data["entity_id"]),
            status=data["status"],
            fields=fields,
            reason=data.get("reason"),
            priority=data.get("priority", "normal"),
            created_at=data["created_at"],
            created_by=UUID(data["created_by"]),
            updated_at=data.get("updated_at"),
        )

    def _generate_diff(self, original: Any, proposed: Any) -> str:
        """Generate unified diff HTML for two values."""
        original_str = str(original) if original is not None else ""
        proposed_str = str(proposed) if proposed is not None else ""

        if original_str == proposed_str:
            return ""

        diff_lines = list(
            unified_diff(
                original_str.splitlines(keepends=True),
                proposed_str.splitlines(keepends=True),
                fromfile="original",
                tofile="proposed",
            )
        )

        # Simple HTML formatting
        html_lines = []
        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                html_lines.append(f'<span class="diff-add">{line}</span>')
            elif line.startswith("-") and not line.startswith("---"):
                html_lines.append(f'<span class="diff-remove">{line}</span>')
            else:
                html_lines.append(f"<span>{line}</span>")

        return "".join(html_lines)
