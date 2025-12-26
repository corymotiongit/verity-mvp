"""
Tests for Verity API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from verity.config import get_settings
from verity.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def _force_legacy_compat(monkeypatch):
    """These tests target legacy endpoints (e.g. /agent/*).

    Force legacy compat on so expectations remain stable even if a developer
    runs tests with LEGACY_COMPAT_ENABLED=false in their local .env.
    """
    monkeypatch.setenv("LEGACY_COMPAT_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestHealth:
    """Health check tests."""

    def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "features" in data

    def test_health_includes_features(self, client):
        """Test health endpoint includes feature flags."""
        response = client.get("/health")
        data = response.json()

        features = data["features"]
        assert isinstance(features, dict)
        assert "documents" in features
        assert "approvals" in features
        assert "agent" in features


class TestRoot:
    """Root endpoint tests."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "docs" in data


class TestOpenAPI:
    """OpenAPI schema tests."""

    def test_openapi_available(self, client):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert data["openapi"].startswith("3.")
        assert data["info"]["title"] == "Verity API"

    def test_docs_available(self, client):
        """Test Swagger UI is available."""
        response = client.get("/docs")
        assert response.status_code == 200


class TestDocumentsModule:
    """Documents module tests (requires auth)."""

    def test_documents_requires_auth(self, client):
        """Test documents endpoints require authentication."""
        response = client.get("/documents")
        assert response.status_code == 401

    def test_search_requires_auth(self, client):
        """Test search endpoint requires authentication."""
        response = client.post(
            "/documents/search",
            json={"query": "test"}
        )
        assert response.status_code == 401


class TestApprovalsModule:
    """Approvals module tests (requires auth)."""

    def test_approvals_requires_auth(self, client):
        """Test approvals endpoints require authentication."""
        response = client.get("/approvals")
        assert response.status_code == 401

    def test_pending_requires_auth(self, client):
        """Test pending endpoint requires authentication."""
        response = client.get("/approvals/pending")
        assert response.status_code == 401


class TestAgentModule:
    """Agent module tests (requires auth)."""

    def test_chat_requires_auth(self, client):
        """Test chat endpoint requires authentication."""
        response = client.post(
            "/agent/chat",
            json={"message": "Hello Veri"}
        )
        assert response.status_code == 401


class TestChartsModule:
    """Charts module tests (requires auth)."""

    def test_generate_requires_auth(self, client):
        """Test generate endpoint requires authentication."""
        response = client.post(
            "/charts/generate",
            json={"data": [{"x": 1, "y": 2}]}
        )
        assert response.status_code == 401


class TestLogsModule:
    """Logs module tests (requires admin)."""

    def test_logs_requires_auth(self, client):
        """Test logs endpoint requires authentication."""
        response = client.get("/logs")
        assert response.status_code == 401


class TestAuditModule:
    """Audit module tests (requires auditor role)."""

    def test_timeline_requires_auth(self, client):
        """Test timeline endpoint requires authentication."""
        response = client.get("/audit/timeline")
        assert response.status_code == 401
