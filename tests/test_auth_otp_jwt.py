"""OTP validate issues JWT access tokens.

This validates the new auth direction:
- OTP is validated via n8n (mocked here via AUTH_INSECURE_DEV_BYPASS)
- FastAPI issues a short-lived JWT access token
- The rest of the API can authenticate with that JWT without Redis
"""

from fastapi.testclient import TestClient

from verity.config import get_settings
from verity.main import app


def test_otp_validate_mock_issues_access_token_and_jwt_auth_works(monkeypatch):
    # Ensure legacy endpoints are available during this legacy-contract test.
    monkeypatch.setenv("LEGACY_COMPAT_ENABLED", "true")

    # Step 1: enable OTP mock mode to get a token without n8n/WhatsApp.
    monkeypatch.setenv("AUTH_INSECURE_DEV_BYPASS", "true")
    get_settings.cache_clear()

    client = TestClient(app)

    bad = client.post("/otp/validate", json={"userId": "user-1", "otp": "000000"})
    assert bad.status_code == 401

    ok = client.post("/otp/validate", json={"userId": "user-1", "otp": "123456"})
    assert ok.status_code == 200
    body = ok.json()
    assert body.get("ok") is True
    assert isinstance(body.get("access_token"), str) and body["access_token"]
    assert body.get("token_type") == "bearer"
    assert isinstance(body.get("expires_in"), int) and body["expires_in"] > 0

    access_token = body["access_token"]

    # Step 2: disable bypass so auth is enforced, and prove JWT works without Redis.
    monkeypatch.setenv("AUTH_INSECURE_DEV_BYPASS", "false")
    get_settings.cache_clear()

    unauth = client.get("/agent/conversations")
    assert unauth.status_code == 401

    authed = client.get(
        "/agent/conversations",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert authed.status_code == 200
    payload = authed.json()
    assert "items" in payload
    assert "meta" in payload

    # Restore cache for other tests
    get_settings.cache_clear()
