"""
Verity Logs - Service.

Log retrieval service. READ-ONLY, no arbitrary filters to prevent leaks.
"""

from collections import deque
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

import structlog

from verity.modules.logs.schemas import LogEntry, LogLevel


# In-memory log buffer for demo (in production, use Cloud Logging)
_log_buffer: deque[LogEntry] = deque(maxlen=1000)


def add_log_entry(
    level: LogLevel,
    message: str,
    logger: str | None = None,
    request_id: UUID | None = None,
    user_id: UUID | None = None,
    extra: dict | None = None,
) -> None:
    """Add a log entry to the buffer."""
    entry = LogEntry(
        timestamp=datetime.now(timezone.utc),
        level=level,
        message=message,
        logger=logger,
        request_id=request_id,
        user_id=user_id,
        extra=extra,
    )
    _log_buffer.append(entry)


class LogsService:
    """Service for log retrieval. READ-ONLY."""

    async def list_logs(
        self,
        level: LogLevel | None = None,
        since: datetime | None = None,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> tuple[list[LogEntry], str | None, int]:
        """
        List logs with limited filtering.

        Only allows filtering by level and since (no arbitrary filters).
        """
        offset = int(page_token) if page_token else 0

        # Get logs from buffer
        logs = list(_log_buffer)

        # Filter by level (fixed filter, not arbitrary)
        if level:
            level_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            min_level_idx = level_order.index(level)
            logs = [
                log for log in logs
                if level_order.index(log.level) >= min_level_idx
            ]

        # Filter by since
        if since:
            logs = [log for log in logs if log.timestamp >= since]

        # Sort by timestamp descending
        logs.sort(key=lambda x: x.timestamp, reverse=True)

        # Paginate
        total = len(logs)
        logs = logs[offset : offset + page_size]

        next_token = None
        if offset + len(logs) < total:
            next_token = str(offset + page_size)

        return logs, next_token, total

    async def stream_logs(
        self,
        level: LogLevel | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream logs as SSE events (terminal style).

        Only filters by level (fixed filter).
        """
        import asyncio

        # Track last seen index
        last_idx = len(_log_buffer)

        level_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        min_level_idx = level_order.index(level) if level else 0

        while True:
            # Check for new logs
            current_len = len(_log_buffer)
            if current_len > last_idx:
                # Get new logs
                new_logs = list(_log_buffer)[last_idx:current_len]
                last_idx = current_len

                for log in new_logs:
                    # Filter by level
                    if level_order.index(log.level) >= min_level_idx:
                        # Format as terminal-style output
                        formatted = self._format_log_line(log)
                        yield f"data: {formatted}\n\n"

            # Wait before checking again
            await asyncio.sleep(0.5)

    def _format_log_line(self, log: LogEntry) -> str:
        """Format log entry as terminal-style line."""
        timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level_colors = {
            "DEBUG": "37",    # White
            "INFO": "32",     # Green
            "WARNING": "33",  # Yellow
            "ERROR": "31",    # Red
            "CRITICAL": "35", # Magenta
        }
        color = level_colors.get(log.level, "0")

        # ANSI escape codes for terminal display
        return f"[{timestamp}] \033[{color}m{log.level:8}\033[0m {log.message}"
