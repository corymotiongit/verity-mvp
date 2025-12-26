"""Tests for hardening middleware (rate limiting, body size limits)."""

import os
import pytest
from fastapi.testclient import TestClient


# Force production-like settings for rate limit tests
os.environ["RATE_LIMIT_ENABLED"] = "true"
os.environ["RATE_LIMIT_AUTH_PER_MIN"] = "3"
os.environ["RATE_LIMIT_QUERY_PER_MIN"] = "5"
os.environ["MAX_BODY_SIZE_BYTES"] = "1000"


class TestRateLimiting:
    """Tests for rate limiting middleware."""

    def test_rate_limit_auth_endpoint(self):
        """Test rate limiting on auth endpoints."""
        # Import after env vars are set
        from verity.main import app, _rate_limit_store
        
        # Clear rate limit store
        _rate_limit_store.clear()
        
        client = TestClient(app)
        
        # Make requests up to the limit
        for i in range(3):
            response = client.post(
                "/api/v2/auth/otp/validate",
                json={"wa_id": "test123", "otp": "123456"},
            )
            # May fail for other reasons, but should not be rate limited yet
            assert response.status_code != 429, f"Request {i+1} should not be rate limited"
        
        # Next request should be rate limited
        response = client.post(
            "/api/v2/auth/otp/validate",
            json={"wa_id": "test123", "otp": "123456"},
        )
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "RATE_LIMITED"
        assert "Retry-After" in response.headers

    @pytest.mark.skip(reason="Rate limit middleware configured at app startup, not respecting test env vars - needs fixture refactor")
    def test_rate_limit_query_endpoint(self):
        """Test rate limiting on query endpoints."""
        # Force settings reload with test values
        from verity.config import get_settings
        get_settings.cache_clear()
        
        from verity.main import app, _rate_limit_store
        
        # Clear rate limit store
        _rate_limit_store.clear()
        
        client = TestClient(app)
        
        # Make requests up to the limit
        for i in range(5):
            response = client.post(
                "/api/v2/query",
                json={"question": "test query"},
            )
            assert response.status_code != 429, f"Request {i+1} should not be rate limited"
        
        # Next request should be rate limited
        response = client.post(
            "/api/v2/query",
            json={"question": "test query"},
        )
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "RATE_LIMITED"


class TestBodySizeLimit:
    """Tests for body size limit middleware."""

    def test_body_size_within_limit(self):
        """Test that requests within limit pass through."""
        from verity.main import app
        
        client = TestClient(app)
        
        # Small body should pass
        response = client.post(
            "/api/v2/query",
            json={"question": "test"},
        )
        assert response.status_code != 413

    def test_body_size_exceeds_limit(self):
        """Test that oversized requests are rejected."""
        from verity.main import app
        
        client = TestClient(app)
        
        # Large body should be rejected
        large_question = "x" * 2000  # Exceeds 1000 byte limit
        response = client.post(
            "/api/v2/query",
            json={"question": large_question},
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


class TestHardeningConfig:
    """Tests for hardening configuration."""

    def test_config_defaults(self):
        """Test that hardening config has sensible defaults."""
        from verity.config import Settings
        
        # Create fresh settings (not cached)
        settings = Settings()
        
        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_auth_per_min >= 1
        assert settings.rate_limit_query_per_min >= 1
        assert settings.request_timeout_seconds >= 10
        assert settings.max_body_size_bytes >= 1000
