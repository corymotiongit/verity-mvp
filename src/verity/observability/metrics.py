"""
Verity Metrics Store.

In-process metrics collection for observability without external dependencies.
Tracks:
- Tool latencies (per tool, histograms/percentiles)
- Error counts by code (VerityException.code)
- OTP attempts by wa_id with TTL tracking

Thread-safe via locks. Singleton pattern for global access.
"""

from __future__ import annotations

import statistics
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any


@dataclass
class ToolMetrics:
    """Metrics for a single tool."""

    latencies_ms: list[float] = field(default_factory=list)
    error_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    call_count: int = 0
    last_called: datetime | None = None

    # Keep last N latencies to avoid unbounded memory
    MAX_LATENCIES = 1000

    def record_latency(self, ms: float) -> None:
        self.latencies_ms.append(ms)
        if len(self.latencies_ms) > self.MAX_LATENCIES:
            self.latencies_ms = self.latencies_ms[-self.MAX_LATENCIES :]
        self.call_count += 1
        self.last_called = datetime.now(timezone.utc)

    def record_error(self, code: str) -> None:
        self.error_counts[code] += 1

    def get_percentiles(self) -> dict[str, float]:
        if not self.latencies_ms:
            return {}
        sorted_latencies = sorted(self.latencies_ms)
        n = len(sorted_latencies)
        return {
            "p50_ms": sorted_latencies[int(n * 0.5)] if n > 0 else 0,
            "p90_ms": sorted_latencies[int(n * 0.9)] if n > 0 else 0,
            "p99_ms": sorted_latencies[int(n * 0.99)] if n > 1 else sorted_latencies[-1] if n > 0 else 0,
            "mean_ms": statistics.mean(sorted_latencies) if n > 0 else 0,
            "max_ms": max(sorted_latencies) if n > 0 else 0,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_count": self.call_count,
            "last_called": self.last_called.isoformat() if self.last_called else None,
            **self.get_percentiles(),
            "errors": dict(self.error_counts),
        }


@dataclass
class OtpAttempt:
    """Single OTP attempt record."""

    timestamp: datetime
    success: bool
    error_code: str | None = None


class MetricsStore:
    """
    Central metrics store for Verity observability.

    Thread-safe singleton for collecting metrics across the application.
    """

    def __init__(self, otp_window_seconds: int = 3600):
        self._lock = threading.Lock()
        self._tools: dict[str, ToolMetrics] = defaultdict(ToolMetrics)
        self._global_errors: dict[str, int] = defaultdict(int)
        self._otp_attempts: dict[str, list[OtpAttempt]] = defaultdict(list)
        self._otp_window_seconds = otp_window_seconds
        self._started_at = datetime.now(timezone.utc)

    # -------------------------------------------------------------------------
    # Tool Metrics
    # -------------------------------------------------------------------------

    def record_tool_latency(self, tool: str, ms: float) -> None:
        """Record a tool execution latency."""
        with self._lock:
            self._tools[tool].record_latency(ms)

    def record_tool_error(self, tool: str, code: str) -> None:
        """Record an error for a specific tool."""
        with self._lock:
            self._tools[tool].record_error(code)
            self._global_errors[code] += 1

    # -------------------------------------------------------------------------
    # Global Errors
    # -------------------------------------------------------------------------

    def record_error(self, code: str) -> None:
        """Record a global error (not tied to a specific tool)."""
        with self._lock:
            self._global_errors[code] += 1

    # -------------------------------------------------------------------------
    # OTP Metrics
    # -------------------------------------------------------------------------

    def record_otp_attempt(
        self, wa_id: str, success: bool, error_code: str | None = None
    ) -> None:
        """Record an OTP validation attempt."""
        with self._lock:
            self._otp_attempts[wa_id].append(
                OtpAttempt(
                    timestamp=datetime.now(timezone.utc),
                    success=success,
                    error_code=error_code,
                )
            )
            # Prune old attempts outside the window
            self._prune_otp_attempts(wa_id)

    def _prune_otp_attempts(self, wa_id: str) -> None:
        """Remove OTP attempts older than the window. Must hold lock."""
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - self._otp_window_seconds
        self._otp_attempts[wa_id] = [
            a for a in self._otp_attempts[wa_id] if a.timestamp.timestamp() > cutoff
        ]

    def get_otp_attempts_count(self, wa_id: str) -> int:
        """Get count of OTP attempts for a wa_id in the current window."""
        with self._lock:
            self._prune_otp_attempts(wa_id)
            return len(self._otp_attempts[wa_id])

    # -------------------------------------------------------------------------
    # Summary / Export
    # -------------------------------------------------------------------------

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of all metrics.

        Returns a dict suitable for JSON serialization and /metrics endpoint.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            uptime_seconds = (now - self._started_at).total_seconds()

            # Aggregate OTP stats
            total_otp_attempts = sum(len(attempts) for attempts in self._otp_attempts.values())
            unique_wa_ids = len(self._otp_attempts)
            otp_success_count = sum(
                1 for attempts in self._otp_attempts.values() for a in attempts if a.success
            )
            otp_error_counts: dict[str, int] = defaultdict(int)
            for attempts in self._otp_attempts.values():
                for a in attempts:
                    if a.error_code:
                        otp_error_counts[a.error_code] += 1

            return {
                "uptime_seconds": round(uptime_seconds, 1),
                "collected_at": now.isoformat(),
                "tools": {name: metrics.to_dict() for name, metrics in self._tools.items()},
                "global_errors": dict(self._global_errors),
                "otp": {
                    "attempts_in_window": total_otp_attempts,
                    "unique_wa_ids": unique_wa_ids,
                    "success_count": otp_success_count,
                    "error_counts": dict(otp_error_counts),
                    "window_seconds": self._otp_window_seconds,
                },
            }

    def reset(self) -> None:
        """Reset all metrics. Useful for testing."""
        with self._lock:
            self._tools.clear()
            self._global_errors.clear()
            self._otp_attempts.clear()
            self._started_at = datetime.now(timezone.utc)


# -----------------------------------------------------------------------------
# Singleton accessor
# -----------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_metrics_store() -> MetricsStore:
    """Get the global MetricsStore singleton."""
    return MetricsStore()
