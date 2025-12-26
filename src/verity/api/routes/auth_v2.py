"""Verity v2 Auth Routes.

Implements the OTP validation flow described in the architecture:
- n8n is the only component that validates OTPs and interacts with WhatsApp.
- Redis is used by n8n for OTP storage and attempts/TTL.
- FastAPI proxies validation to n8n, rate-limits, upserts identity in Supabase, and issues a short-lived JWT.

Errors are unified under:
{ "error": { "code": "...", "message": "..." } }

Legacy endpoints under /otp/* remain temporarily for frontend compatibility.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from verity.auth import create_access_token
from verity.config import Settings, get_settings
from verity.core.users_repository import upsert_user_identity
from verity.exceptions import VerityException
from verity.observability import get_metrics_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/auth", tags=["v2-auth"])


class OtpValidateV2In(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wa_id: str = Field(min_length=1)
    otp: str = Field(min_length=1)


class OtpValidateV2Out(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


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


def _raise_auth_error(*, code: str, request_id: str) -> None:
    # Minimal, user-facing messages (avoid leaking provider internals).
    messages: dict[str, str] = {
        "OTP_INVALID": "Código incorrecto.",
        "OTP_EXPIRED": "El código expiró. Solicita uno nuevo.",
        "OTP_RATE_LIMITED": "Demasiados intentos. Intenta más tarde.",
        "WHATSAPP_PROVIDER_DOWN": "El proveedor de WhatsApp no está disponible.",
        "BAD_N8N_RESPONSE": "Respuesta inválida del proveedor.",
    }

    raise VerityException(
        code=code,
        message=messages.get(code, "Error de autenticación."),
        status_code={
            "OTP_INVALID": 401,
            "OTP_EXPIRED": 401,
            "OTP_RATE_LIMITED": 429,
            "WHATSAPP_PROVIDER_DOWN": 503,
            "BAD_N8N_RESPONSE": 502,
        }.get(code, 400),
        details={"request_id": request_id},
    )


@router.post("/otp/validate", response_model=OtpValidateV2Out)
async def otp_validate_v2(
    payload: OtpValidateV2In,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> OtpValidateV2Out:
    """Validate OTP via n8n, upsert identity in Supabase, and issue JWT."""

    request_id = getattr(request.state, "request_id", "unknown")

    if settings.auth_otp_insecure_dev_bypass and not settings.is_production:
        logger.warning("[%s] V2_OTP_VALIDATE wa_id=%s -> insecure_dev_bypass", request_id, payload.wa_id)
        now = datetime.now(timezone.utc)
        try:
            upsert_user_identity(wa_id=payload.wa_id, phone_number=None, last_login=now)
        except Exception as e:
            logger.warning(
                "[%s] V2_OTP_VALIDATE wa_id=%s -> bypass_identity_upsert_failed: %s",
                request_id,
                payload.wa_id,
                str(e),
            )
        access_token, expires_in = create_access_token(
            settings=settings,
            user_id_raw=payload.wa_id,
            roles=["user"],
            now=now,
        )
        get_metrics_store().record_otp_attempt(payload.wa_id, success=True)
        return OtpValidateV2Out(access_token=access_token, expires_in=expires_in)

    if not (settings.n8n.base_url or "").strip():
        logger.warning(f"[{request_id}] V2_OTP_VALIDATE wa_id={payload.wa_id} -> missing_n8n_base_url")
        _raise_auth_error(code="WHATSAPP_PROVIDER_DOWN", request_id=request_id)

    url = _n8n_url(settings.n8n.base_url, settings.n8n.otp_validate_path)

    # Definitive contract: FastAPI sends wa_id + otp to n8n.
    result = await _post_json(
        url,
        {"wa_id": payload.wa_id, "otp": payload.otp},
        settings.n8n.timeout_seconds,
    )

    if result is None:
        logger.warning(f"[{request_id}] V2_OTP_VALIDATE wa_id={payload.wa_id} -> provider_down")
        _raise_auth_error(code="WHATSAPP_PROVIDER_DOWN", request_id=request_id)

    status_code, data = result
    if not isinstance(data, dict):
        logger.warning(
            f"[{request_id}] V2_OTP_VALIDATE wa_id={payload.wa_id} -> bad_n8n_response status={status_code}"
        )
        _raise_auth_error(code="BAD_N8N_RESPONSE", request_id=request_id)

    ok = data.get("ok") is True
    if not ok:
        error_code = data.get("error_code") if isinstance(data.get("error_code"), str) else "OTP_INVALID"
        if error_code not in {"OTP_INVALID", "OTP_EXPIRED", "OTP_RATE_LIMITED"}:
            error_code = "OTP_INVALID"
        logger.info(f"[{request_id}] V2_OTP_VALIDATE wa_id={payload.wa_id} -> fail {error_code}")
        get_metrics_store().record_otp_attempt(payload.wa_id, success=False, error_code=error_code)
        _raise_auth_error(code=error_code, request_id=request_id)

    wa_id = data.get("wa_id") if isinstance(data.get("wa_id"), str) else payload.wa_id
    phone_number = data.get("phone_number") if isinstance(data.get("phone_number"), str) else None

    # Persist identity (never OTP).
    now = datetime.now(timezone.utc)
    try:
        upsert_user_identity(wa_id=wa_id, phone_number=phone_number, last_login=now)
    except VerityException:
        raise
    except Exception as e:
        raise VerityException(
            code="IDENTITY_UPSERT_FAILED",
            message="No se pudo actualizar el usuario.",
            status_code=502,
            details={"request_id": request_id, "cause": str(e)},
        )

    access_token, expires_in = create_access_token(
        settings=settings,
        user_id_raw=wa_id,
        roles=["user"],
        now=now,
    )

    logger.info(f"[{request_id}] V2_OTP_VALIDATE wa_id={wa_id} -> ok")
    get_metrics_store().record_otp_attempt(wa_id, success=True)

    return OtpValidateV2Out(access_token=access_token, expires_in=expires_in)
