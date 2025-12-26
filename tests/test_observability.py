"""Tests for observability metrics module."""

import pytest
from verity.observability.metrics import MetricsStore


class TestToolMetrics:
    """Tests for tool-level metrics."""

    def test_record_latency(self):
        store = MetricsStore()
        store.record_tool_latency("test_tool@1.0", 50.0)
        store.record_tool_latency("test_tool@1.0", 100.0)
        store.record_tool_latency("test_tool@1.0", 150.0)

        summary = store.get_summary()
        tool_metrics = summary["tools"]["test_tool@1.0"]

        assert tool_metrics["call_count"] == 3
        assert tool_metrics["p50_ms"] == 100.0
        assert tool_metrics["max_ms"] == 150.0

    def test_record_tool_error(self):
        store = MetricsStore()
        store.record_tool_error("resolve_semantics@1.0", "UNRESOLVED_METRIC")
        store.record_tool_error("resolve_semantics@1.0", "UNRESOLVED_METRIC")
        store.record_tool_error("resolve_semantics@1.0", "AMBIGUOUS_METRIC")

        summary = store.get_summary()
        errors = summary["tools"]["resolve_semantics@1.0"]["errors"]

        assert errors["UNRESOLVED_METRIC"] == 2
        assert errors["AMBIGUOUS_METRIC"] == 1

    def test_global_errors(self):
        store = MetricsStore()
        store.record_error("RATE_LIMITED")
        store.record_error("RATE_LIMITED")
        store.record_error("INTERNAL_ERROR")

        summary = store.get_summary()
        assert summary["global_errors"]["RATE_LIMITED"] == 2
        assert summary["global_errors"]["INTERNAL_ERROR"] == 1


class TestOtpMetrics:
    """Tests for OTP attempt tracking."""

    def test_record_otp_success(self):
        store = MetricsStore()
        store.record_otp_attempt("521234567890", success=True)

        summary = store.get_summary()
        assert summary["otp"]["attempts_in_window"] == 1
        assert summary["otp"]["success_count"] == 1
        assert summary["otp"]["unique_wa_ids"] == 1

    def test_record_otp_failure(self):
        store = MetricsStore()
        store.record_otp_attempt("521234567890", success=False, error_code="OTP_INVALID")
        store.record_otp_attempt("521234567890", success=False, error_code="OTP_EXPIRED")

        summary = store.get_summary()
        assert summary["otp"]["attempts_in_window"] == 2
        assert summary["otp"]["success_count"] == 0
        assert summary["otp"]["error_counts"]["OTP_INVALID"] == 1
        assert summary["otp"]["error_counts"]["OTP_EXPIRED"] == 1

    def test_get_otp_attempts_count(self):
        store = MetricsStore()
        wa_id = "521234567890"
        store.record_otp_attempt(wa_id, success=False, error_code="OTP_INVALID")
        store.record_otp_attempt(wa_id, success=False, error_code="OTP_INVALID")
        store.record_otp_attempt(wa_id, success=False, error_code="OTP_INVALID")

        assert store.get_otp_attempts_count(wa_id) == 3


class TestMetricsSummary:
    """Tests for metrics summary structure."""

    def test_summary_structure(self):
        store = MetricsStore()
        summary = store.get_summary()

        assert "uptime_seconds" in summary
        assert "collected_at" in summary
        assert "tools" in summary
        assert "global_errors" in summary
        assert "otp" in summary
        assert "window_seconds" in summary["otp"]

    def test_reset(self):
        store = MetricsStore()
        store.record_tool_latency("test@1.0", 100.0)
        store.record_error("TEST_ERROR")
        store.record_otp_attempt("12345", success=True)

        store.reset()
        summary = store.get_summary()

        assert summary["tools"] == {}
        assert summary["global_errors"] == {}
        assert summary["otp"]["attempts_in_window"] == 0
