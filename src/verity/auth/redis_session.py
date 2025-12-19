"""Verity Auth - Redis Session Validation.

Validates opaque session tokens (Bearer) by looking them up in Redis.

Expected Redis key format (configurable):
- key = <REDIS_SESSION_KEY_PREFIX> + <sessionToken>

Expected value formats:
- JSON object (recommended). Example:
  {
    "userId": "...",
    "orgId": "...",
    "roles": ["user", "admin"],
    "exp": 1735689600
  }
- Plain string: treated as userId

If org context isn't present in the session payload, defaults from settings are used.
"""

from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID, NAMESPACE_URL, uuid5

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from verity.auth.schemas import Organization, User
from verity.config import Settings, get_settings
from verity.exceptions import UnauthorizedException, VerityException

security = HTTPBearer(auto_error=False)


class _SessionPayload(BaseModel):
    userId: str | None = None
    user_id: str | None = None
    orgId: str | None = None
    org_id: str | None = None
    roles: list[str] | None = None
    role: str | None = None
    organization: dict[str, Any] | None = None
    exp: int | None = None


def _safe_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception:
        return uuid5(NAMESPACE_URL, f"verity:user:{value}")


def _decode_session_value(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, (bytes, bytearray)):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = str(raw)

    text = text.strip()
    if not text:
        return {}

    if text.startswith("{"):
        try:
            loaded = json.loads(text)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}

    # Plain string = userId
    return {"userId": text}


def _normalize_roles(data: dict[str, Any]) -> list[str]:
    roles = data.get("roles")
    if isinstance(roles, list) and all(isinstance(r, str) for r in roles):
        return roles

    role = data.get("role")
    if isinstance(role, str) and role:
        return [role]

    return ["user"]


async def _get_redis(settings: Settings):
    try:
        import redis.asyncio as redis  # type: ignore

        return redis.Redis.from_url(settings.redis.url, decode_responses=False)
    except Exception as e:
        raise VerityException(
            code="AUTH_PROVIDER_DOWN",
            message=f"Redis client init failed: {e}",
            status_code=503,
        )


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    # Local MVP bypass: allow running without Redis/session provisioning.
    # OFF by default; enable via AUTH_INSECURE_DEV_BYPASS=true.
    if settings.auth_insecure_dev_bypass and not settings.is_production:
        # Use a stable identity so local conversations/charts persist across reloads
        # and do not depend on which token happened to be used.
        user_id_raw = "local-dev-user"
        org_id_raw = settings.redis.default_org_id
        org_id = _safe_uuid(org_id_raw)
        organization = Organization(
            id=org_id,
            name=settings.redis.default_org_name,
            slug=settings.redis.default_org_slug,
            file_search_store_id=settings.redis.default_file_search_store_id,
            settings={},
        )
        user = User(
            id=_safe_uuid(user_id_raw),
            email=None,
            org_id=org_id,
            organization=organization,
            display_name="Local Dev",
            roles=["admin"],
        )
        request.state.user = user.model_dump()
        return user

    token = (credentials.credentials or "").strip() if credentials else ""

    # Local MVP convenience: accept a known mock token without Redis.
    # This keeps the demo unblocked even if env flags are not set.
    if (not settings.is_production) and token == "local-dev-token":
        org_id_raw = settings.redis.default_org_id
        org_id = _safe_uuid(org_id_raw)
        organization = Organization(
            id=org_id,
            name=settings.redis.default_org_name,
            slug=settings.redis.default_org_slug,
            file_search_store_id=settings.redis.default_file_search_store_id,
            settings={},
        )
        user = User(
            id=_safe_uuid("local-dev-user"),
            email=None,
            org_id=org_id,
            organization=organization,
            display_name="Local Dev",
            roles=["admin"],
        )
        request.state.user = user.model_dump()
        return user

    if not credentials:
        raise UnauthorizedException("Missing authentication token")

    if not token or any(ch.isspace() for ch in token):
        raise UnauthorizedException("Invalid authentication token")

    redis_client = await _get_redis(settings)

    key = f"{settings.redis.session_key_prefix}{token}"
    try:
        raw = await redis_client.get(key)
    except Exception as e:
        raise VerityException(
            code="AUTH_PROVIDER_DOWN",
            message=f"Redis GET failed: {e}",
            status_code=503,
        )

    if raw is None:
        raise UnauthorizedException("Invalid or expired session")

    data = _decode_session_value(raw)
    payload = _SessionPayload.model_validate(data)

    user_id_raw = payload.userId or payload.user_id
    if not user_id_raw:
        raise UnauthorizedException("Malformed session")

    org_id_raw = payload.orgId or payload.org_id or settings.redis.default_org_id

    roles = _normalize_roles(data)

    # Organization context (MVP defaults if missing)
    org_dict: dict[str, Any] = {}
    if isinstance(payload.organization, dict):
        org_dict = payload.organization

    org_id = _safe_uuid(str(org_dict.get("id") or org_id_raw))
    org_name = str(org_dict.get("name") or settings.redis.default_org_name)
    org_slug = str(org_dict.get("slug") or settings.redis.default_org_slug)
    file_search_store_id = org_dict.get("file_search_store_id") or org_dict.get("fileSearchStoreId")
    if not isinstance(file_search_store_id, str) or not file_search_store_id:
        file_search_store_id = settings.redis.default_file_search_store_id

    organization = Organization(
        id=org_id,
        name=org_name,
        slug=org_slug,
        file_search_store_id=file_search_store_id,
        settings={},
    )

    user = User(
        id=_safe_uuid(user_id_raw),
        email=str(data.get("email")) if isinstance(data.get("email"), str) else None,
        org_id=org_id,
        organization=organization,
        display_name=str(data.get("display_name")) if isinstance(data.get("display_name"), str) else None,
        roles=roles,
    )

    # Store user in request state for other deps
    request.state.user = user.model_dump()

    return user


async def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User | None:
    if not credentials:
        return None

    try:
        return await get_current_user(request, credentials, settings)
    except UnauthorizedException:
        return None
