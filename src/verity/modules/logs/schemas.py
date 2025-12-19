"""
Verity Logs - Schemas.

Pydantic models for log operations.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from verity.schemas import PaginationMeta


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogEntry(BaseModel):
    """Single log entry."""

    timestamp: datetime
    level: LogLevel
    message: str
    logger: str | None = None
    request_id: UUID | None = None
    user_id: UUID | None = None
    extra: dict[str, Any] | None = None


class LogListResponse(BaseModel):
    """Paginated list of logs."""

    items: list[LogEntry]
    meta: PaginationMeta
