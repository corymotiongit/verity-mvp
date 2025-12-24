"""Verity Auth - FastAPI-issued JWT access tokens.

This module implements:
- Issuing short-lived JWTs (HS256 by default)
- A FastAPI dependency to authenticate requests using these tokens

Design goal:
- Accept JWT access tokens without requiring Redis.
- Keep backwards compatibility with the existing Redis session token auth.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID, NAMESPACE_URL, uuid5

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from verity.auth.schemas import Organization, User
from verity.config import Settings, get_settings
from verity.exceptions import UnauthorizedException

security = HTTPBearer(auto_error=False)


def _safe_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception:
        return uuid5(NAMESPACE_URL, f"verity:user:{value}")


def create_access_token(
    *,
    settings: Settings,
    user_id_raw: str,
    org_id_raw: str | None = None,
    roles: list[str] | None = None,
    now: datetime | None = None,
) -> tuple[str, int]:
    """Create a signed access token and return (token, expires_in_seconds)."""

    if now is None:
        now = datetime.now(timezone.utc)

    ttl_s = int(settings.auth_access_token_ttl_seconds)
    exp = now + timedelta(seconds=ttl_s)

    org_id_raw = org_id_raw or settings.redis.default_org_id
    roles = roles or ["user"]

    payload: dict[str, Any] = {
        "sub": str(_safe_uuid(user_id_raw)),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "org_id": str(_safe_uuid(org_id_raw)),
        "roles": roles,
        "typ": "access",
        "iss": "verity",
    }

    token = jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)
    return token, ttl_s


def _decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.auth_jwt_secret, algorithms=[settings.auth_jwt_algorithm])
    except JWTError as e:
        raise UnauthorizedException(f"Invalid token: {e}")

    if payload.get("typ") != "access":
        raise UnauthorizedException("Invalid token type")

    return payload


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """Authenticate using a FastAPI-issued JWT access token."""

    if not credentials:
        raise UnauthorizedException("Missing authentication token")

    token = (credentials.credentials or "").strip()
    if not token or any(ch.isspace() for ch in token):
        raise UnauthorizedException("Invalid authentication token")

    payload = _decode_access_token(token, settings)

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise UnauthorizedException("Malformed token payload")

    org_id = payload.get("org_id")
    org_id_raw = str(org_id) if org_id is not None else settings.redis.default_org_id

    roles_raw = payload.get("roles")
    roles: list[str]
    if isinstance(roles_raw, list) and all(isinstance(r, str) for r in roles_raw):
        roles = roles_raw
    else:
        roles = ["user"]

    org_uuid = _safe_uuid(org_id_raw)
    organization = Organization(
        id=org_uuid,
        name=settings.redis.default_org_name,
        slug=settings.redis.default_org_slug,
        file_search_store_id=settings.redis.default_file_search_store_id,
        settings={},
    )

    user = User(
        id=_safe_uuid(sub),
        email=None,
        org_id=org_uuid,
        organization=organization,
        display_name=None,
        roles=roles,
    )

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
