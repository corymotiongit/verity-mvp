"""
Verity Logs - Router.

API endpoints for logs. ADMIN ONLY, READ-ONLY.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from verity.auth import User, get_current_user
from verity.deps import require_admin, require_logs
from verity.modules.logs.schemas import LogLevel, LogListResponse
from verity.modules.logs.service import LogsService
from verity.schemas import PaginationMeta

router = APIRouter(
    prefix="/logs",
    tags=["logs"],
    dependencies=[require_logs, require_admin],  # Admin only
)


def get_service() -> LogsService:
    """Get logs service instance."""
    return LogsService()


@router.get("", response_model=LogListResponse)
async def list_logs(
    level: LogLevel | None = None,
    since: datetime | None = None,
    page_size: int = 50,
    page_token: str | None = None,
    user: User = Depends(get_current_user),
    service: LogsService = Depends(get_service),
):
    """
    List logs. ADMIN ONLY, READ-ONLY.

    Only fixed filters allowed (level, since) to prevent leaks.
    """
    items, next_token, total = await service.list_logs(
        level=level,
        since=since,
        page_size=page_size,
        page_token=page_token,
    )
    return LogListResponse(
        items=items,
        meta=PaginationMeta(
            total_count=total,
            page_size=page_size,
            next_page_token=next_token,
            has_more=next_token is not None,
        ),
    )


@router.get("/stream")
async def stream_logs(
    level: LogLevel | None = None,
    user: User = Depends(get_current_user),
    service: LogsService = Depends(get_service),
):
    """
    Stream logs via SSE (terminal style). ADMIN ONLY, READ-ONLY.

    Only level filter allowed (fixed filter).
    """
    return EventSourceResponse(service.stream_logs(level=level))
