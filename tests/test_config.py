"""
Tests for configuration module.
"""

import os
import pytest


class TestFeatureFlags:
    """Feature flags tests."""

    def test_default_features_enabled(self):
        """Test all features are enabled by default."""
        from verity.config import FeatureFlags

        flags = FeatureFlags()
        assert flags.documents is True
        assert flags.approvals is True
        assert flags.agent is True
        assert flags.reports is True
        assert flags.charts is True
        assert flags.forecast is True
        assert flags.logs is True
        assert flags.audit is True

    def test_to_dict(self):
        """Test feature flags to dict."""
        from verity.config import FeatureFlags

        flags = FeatureFlags()
        result = flags.to_dict()

        assert isinstance(result, dict)
        assert len(result) == 8
        assert result["documents"] is True


class TestExceptions:
    """Exception tests."""

    def test_unauthorized_exception(self):
        """Test UnauthorizedException."""
        from verity.exceptions import UnauthorizedException

        exc = UnauthorizedException()
        assert exc.status_code == 401
        assert exc.code == "UNAUTHORIZED"

    def test_not_found_exception(self):
        """Test NotFoundException."""
        from verity.exceptions import NotFoundException

        exc = NotFoundException("document", "123")
        assert exc.status_code == 404
        assert exc.code == "NOT_FOUND"
        assert "document" in exc.message

    def test_feature_disabled_exception(self):
        """Test FeatureDisabledException."""
        from verity.exceptions import FeatureDisabledException

        exc = FeatureDisabledException("charts")
        assert exc.status_code == 503
        assert exc.code == "FEATURE_DISABLED"
        assert "charts" in exc.message

    def test_conflict_exception(self):
        """Test ConflictException."""
        from verity.exceptions import ConflictException

        exc = ConflictException(
            "Cannot approve",
            current_state="rejected",
            target_state="approved"
        )
        assert exc.status_code == 409
        assert exc.code == "CONFLICT"
        assert exc.details["current_state"] == "rejected"
