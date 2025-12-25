"""Tests for legacy compatibility flag.

When LEGACY_COMPAT_ENABLED=false, legacy endpoints should return a controlled 410.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from verity.config import get_settings
from verity.main import app


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_legacy_endpoints_return_410_when_disabled(monkeypatch):
    monkeypatch.setenv("LEGACY_COMPAT_ENABLED", "false")
    get_settings.cache_clear()

    client = TestClient(app)

    # legacy agent endpoint
    res = client.post("/agent/chat", json={"message": "hello"})
    assert res.status_code == 410
    body = res.json()
    assert body["error"]["code"] == "LEGACY_DISABLED"

    # legacy otp endpoint
    res2 = client.post("/otp/request", json={"wa_id": "wa-1"})
    assert res2.status_code == 410

    # v2 should still be reachable
    res3 = client.get("/api/v2/health")
    assert res3.status_code == 200
