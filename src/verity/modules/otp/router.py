import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from verity.config import Settings, get_settings

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/otp", tags=["auth"])


class OtpRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    userId: str = Field(min_length=1)
    phone: str = Field(min_length=1)


class OtpValidateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    userId: str = Field(min_length=1)
    otp: str = Field(min_length=1)


def _normalize_phone(phone: str) -> str:
    p = (phone or "").strip()
    # Remove common separators
    for ch in (" ", "-", "(", ")"):
        p = p.replace(ch, "")

    # If looks like digits without '+', prefix '+' (E.164 style)
    if p and not p.startswith("+") and p.isdigit():
        p = "+" + p

    return p


def _n8n_url(base: str, path: str) -> str:
    b = (base or "").strip().rstrip("/")
    p = (path or "").strip()
    if not p.startswith("/"):
        p = "/" + p
    return f"{b}{p}"


async def _post_json(url: str, payload: dict[str, Any], timeout_s: float) -> tuple[int, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
            r = await client.post(url, json=payload)
    except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, httpx.InvalidURL, ValueError):
        return None

    try:
        return r.status_code, r.json()
    except Exception:
        return (r.status_code, None)


async def _get_stored_otp(settings: Settings, user_id: str) -> str | None:
    """Fetch stored OTP from Redis using n8n's key format: otp:<userId>."""
    try:
        import json
        import redis.asyncio as redis  # type: ignore

        client = redis.Redis.from_url(settings.redis.url, decode_responses=False)
        key = f"{settings.redis.otp_key_prefix}{user_id}"
        raw = await client.get(key)
        if raw is None:
            return None
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
        text = (text or "").strip()
        if not text:
            return None

        # n8n stores JSON string: { otp, expiresAt, attempts }
        if text.startswith("{"):
            try:
                data = json.loads(text)
                if isinstance(data, dict) and isinstance(data.get("otp"), str):
                    return data["otp"]
            except Exception:
                return None

        # fallback: raw value is the OTP itself
        return text
    except Exception:
        return None


@router.post("/request")
async def otp_request(payload: OtpRequestIn, request: Request, settings: Settings = Depends(get_settings)):
    """Proxy OTP request to n8n. FastAPI never generates OTP and never sends WhatsApp."""
    request_id = getattr(request.state, "request_id", "unknown")

    # Local MVP mock: avoid n8n/WhatsApp dependencies.
    if settings.auth_insecure_dev_bypass and not settings.is_production:
        phone = _normalize_phone(payload.phone)
        if not phone:
            return JSONResponse(status_code=422, content={"ok": False, "error": "PHONE_INVALID"})

        logger.info(f"[{request_id}] OTP_REQUEST (mock) userId={payload.userId} -> ok")
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "success": True,
                "message": "OTP enviado (mock)",
                "expiresAt": None,
                # For demo convenience: return the mock OTP.
                "debugOtp": "123456",
            },
        )

    if not (settings.n8n.base_url or "").strip():
        logger.warning(f"[{request_id}] OTP_REQUEST userId={payload.userId} -> missing_n8n_base_url")
        return JSONResponse(status_code=503, content={"ok": False, "error": "WHATSAPP_PROVIDER_DOWN"})

    phone = _normalize_phone(payload.phone)
    if not phone:
        return JSONResponse(status_code=422, content={"ok": False, "error": "PHONE_INVALID"})

    url = _n8n_url(settings.n8n.base_url, settings.n8n.otp_request_path)
    result = await _post_json(url, {"userId": payload.userId, "phone": phone}, settings.n8n.timeout_seconds)

    if result is None:
        logger.warning(f"[{request_id}] OTP_REQUEST userId={payload.userId} -> provider_down")
        return JSONResponse(status_code=503, content={"ok": False, "error": "WHATSAPP_PROVIDER_DOWN"})

    status_code, data = result
    if not isinstance(data, dict):
        logger.warning(f"[{request_id}] OTP_REQUEST userId={payload.userId} -> bad_n8n_response status={status_code}")
        return JSONResponse(status_code=502, content={"ok": False, "error": "BAD_N8N_RESPONSE"})

    # Adapt to n8n flow response: { success: true, message: 'OTP enviado', otp: '123456' }
    success = bool(data.get("success"))
    message = data.get("message") if isinstance(data.get("message"), str) else None
    expires_at = data.get("expiresAt") if isinstance(data.get("expiresAt"), str) else None
    otp_value = data.get("otp") if isinstance(data.get("otp"), str) else None

    response: dict[str, Any] = {
        "ok": success,
        "success": success,
        "message": message or ("OTP enviado" if success else None),
        "expiresAt": expires_at,
    }

    # Keep parity with current n8n testing: allow echoing OTP only outside production.
    if otp_value and not settings.is_production:
        response["debugOtp"] = otp_value

    if not success:
        response["error"] = data.get("error") if isinstance(data.get("error"), str) else "OTP_REQUEST_FAILED"

    logger.info(f"[{request_id}] OTP_REQUEST userId={payload.userId} -> {status_code}")
    return JSONResponse(status_code=200 if status_code < 500 else status_code, content=response)


@router.post("/validate")
async def otp_validate(payload: OtpValidateIn, request: Request, settings: Settings = Depends(get_settings)):
    """Proxy OTP validate to n8n. FastAPI never validates OTP itself."""
    request_id = getattr(request.state, "request_id", "unknown")

    # Local MVP mock: accept a fixed OTP and return a dummy session token.
    # With AUTH_INSECURE_DEV_BYPASS enabled, the rest of the API won't require Redis anyway.
    if settings.auth_insecure_dev_bypass and not settings.is_production:
        if payload.otp.strip() != "123456":
            logger.info(f"[{request_id}] OTP_VALIDATE (mock) userId={payload.userId} -> fail")
            return JSONResponse(status_code=401, content={"ok": False, "error": "OTP_INVALID"})

        logger.info(f"[{request_id}] OTP_VALIDATE (mock) userId={payload.userId} -> ok")
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "userId": payload.userId,
                "sessionToken": "local-dev-token",
                "expiresAt": None,
            },
        )

    if not (settings.n8n.base_url or "").strip():
        logger.warning(f"[{request_id}] OTP_VALIDATE userId={payload.userId} -> missing_n8n_base_url")
        return JSONResponse(status_code=503, content={"ok": False, "error": "WHATSAPP_PROVIDER_DOWN"})

    url = _n8n_url(settings.n8n.base_url, settings.n8n.otp_validate_path)

    # Adapt to your current n8n validate flow which compares providedOtp === body.stored_otp
    stored_otp = await _get_stored_otp(settings, payload.userId)
    n8n_payload: dict[str, Any] = {"userId": payload.userId, "otp": payload.otp}
    if stored_otp:
        n8n_payload["stored_otp"] = stored_otp
    elif not settings.is_production:
        # MVP/local fallback: if we can't reach Redis, keep the flow unblocked.
        # (Your current n8n validate compares `otp` vs `stored_otp` from body.)
        n8n_payload["stored_otp"] = payload.otp

    result = await _post_json(url, n8n_payload, settings.n8n.timeout_seconds)

    if result is None:
        logger.warning(f"[{request_id}] OTP_VALIDATE userId={payload.userId} -> provider_down")
        return JSONResponse(status_code=503, content={"ok": False, "error": "WHATSAPP_PROVIDER_DOWN"})

    status_code, data = result
    if not isinstance(data, dict):
        logger.warning(f"[{request_id}] OTP_VALIDATE userId={payload.userId} -> bad_n8n_response status={status_code}")
        return JSONResponse(status_code=502, content={"ok": False, "error": "BAD_N8N_RESPONSE"})

    ok = data.get("ok") is True or data.get("isValid") is True or data.get("success") is True
    if ok:
        session_token = data.get("sessionToken")
        expires_at = data.get("expiresAt")
        if not isinstance(session_token, str) or not session_token:
            logger.warning(f"[{request_id}] OTP_VALIDATE userId={payload.userId} -> missing_sessionToken")
            return JSONResponse(status_code=502, content={"ok": False, "error": "BAD_N8N_RESPONSE"})

        logger.info(f"[{request_id}] OTP_VALIDATE userId={payload.userId} -> ok")
        # Return only the fields promised by API (never echo OTP).
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "userId": payload.userId,
                "sessionToken": session_token,
                "expiresAt": expires_at,
            },
        )

    # Fail path
    # Fail path (n8n may return 4xx/5xx with an error/message)
    err = None
    if isinstance(data.get("error"), str):
        err = data.get("error")
    elif isinstance(data.get("message"), str):
        err = data.get("message")

    # Normalize common n8n error text
    if isinstance(err, str) and "OTP" in err.upper() and "INVALID" in err.upper():
        err = "OTP_INVALID"
    if isinstance(err, str) and "INVÁLIDO" in err.lower():
        err = "OTP_INVALID"

    if not isinstance(err, str) or not err:
        err = "OTP_INVALID"

    logger.info(f"[{request_id}] OTP_VALIDATE userId={payload.userId} -> fail {err} status={status_code}")
    return JSONResponse(status_code=401, content={"ok": False, "error": err})
