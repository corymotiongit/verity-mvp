"""
Verity Observability Module.

Provides in-process metrics collection for tools, errors, and OTP attempts.
"""

from verity.observability.metrics import MetricsStore, get_metrics_store

__all__ = ["MetricsStore", "get_metrics_store"]
