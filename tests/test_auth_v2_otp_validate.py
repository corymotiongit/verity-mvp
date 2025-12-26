"""Tests for v2 OTP validate endpoint.

We mock n8n responses and Supabase client calls. Contract:
- n8n -> FastAPI success payload:
  { ok: true, wa_id: str, phone_number: str, sessionToken?: str }
- n8n -> FastAPI error payload:
  { ok: false, error_code: OTP_INVALID|OTP_EXPIRED|OTP_RATE_LIMITED }

FastAPI v2 errors must be unified as:
{ error: { code, message } }
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fastapi.testclient import TestClient

from verity.config import get_settings
from verity.main import app


class _FakeTable:
    def __init__(self):
        self.upserts = []

    def upsert(self, payload, on_conflict=None):
        self.upserts.append((payload, on_conflict))
        return self

    def execute(self):
        return SimpleNamespace(data=[], error=None)


class _FakeSupabase:
    def __init__(self):
        self.users = _FakeTable()

    def table(self, name: str):
        assert name == "users"
        return self.users


@pytest.fixture(autouse=True)
def _clear_settings_cache(monkeypatch):
    # Keep tests deterministic even if local .env enables bypasses.
    monkeypatch.setenv("AUTH_OTP_INSECURE_DEV_BYPASS", "false")
    # Disable rate limiting for these tests to isolate OTP error handling
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()

    # Clear rate limit store
    from verity.main import _rate_limit_store

    _rate_limit_store.clear()
    yield
    get_settings.cache_clear()


def test_v2_otp_validate_success_issues_token_and_upserts(monkeypatch):
    # Mock n8n call
    async def _fake_post_json(url, payload, timeout_s):
        assert payload.get("wa_id") == "wa-123"
        assert payload.get("otp") == "123456"
        return 200, {"ok": True, "wa_id": "wa-123", "phone_number": "+521234"}

    from verity.api.routes import auth_v2

    monkeypatch.setattr(auth_v2, "_post_json", _fake_post_json)

    # Mock Supabase
    fake = _FakeSupabase()
    from verity.core import users_repository

    monkeypatch.setattr(users_repository, "get_supabase_client", lambda: fake)

    client = TestClient(app)
    res = client.post("/api/v2/auth/otp/validate", json={"wa_id": "wa-123", "otp": "123456"})
    assert res.status_code == 200

    body = res.json()
    assert isinstance(body.get("access_token"), str) and body["access_token"]
    assert body.get("token_type") == "bearer"
    assert isinstance(body.get("expires_in"), int) and body["expires_in"] > 0

    assert len(fake.users.upserts) == 1
    payload, on_conflict = fake.users.upserts[0]
    assert on_conflict == "wa_id"
    assert payload["wa_id"] == "wa-123"
    assert payload["phone_number"] == "+521234"
    assert "last_login" in payload


@pytest.mark.parametrize("code,status", [("OTP_INVALID", 401), ("OTP_EXPIRED", 401), ("OTP_RATE_LIMITED", 429)])
def test_v2_otp_validate_errors_are_typed(monkeypatch, code: str, status: int):
    async def _fake_post_json(url, payload, timeout_s):
        return 200, {"ok": False, "error_code": code}

    from verity.api.routes import auth_v2

    monkeypatch.setattr(auth_v2, "_post_json", _fake_post_json)

    client = TestClient(app)
    res = client.post("/api/v2/auth/otp/validate", json={"wa_id": "wa-1", "otp": "000000"})
    assert res.status_code == status

    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
