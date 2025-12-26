"""
Verity v2 Metrics Endpoint.

Exposes observability metrics for monitoring and debugging.
"""

from fastapi import APIRouter

from verity.observability import get_metrics_store

router = APIRouter(prefix="/api/v2", tags=["v2-metrics"])


@router.get("/metrics")
def get_metrics() -> dict:
    """
    Get current metrics summary.

    Returns metrics for:
    - Tool latencies (p50, p90, p99, mean, max)
    - Error counts by code
    - OTP attempts within the last hour

    Example response:
    ```json
    {
      "uptime_seconds": 3600.5,
      "collected_at": "2025-12-25T19:00:00Z",
      "tools": {
        "resolve_semantics@1.0": {
          "call_count": 150,
          "p50_ms": 45.2,
          "p99_ms": 120.5,
          "errors": {"UNRESOLVED_METRIC": 3}
        }
      },
      "global_errors": {"RATE_LIMITED": 5},
      "otp": {
        "attempts_in_window": 12,
        "unique_wa_ids": 5,
        "success_count": 10,
        "error_counts": {"OTP_INVALID": 2}
      }
    }
    ```
    """
    return get_metrics_store().get_summary()
