"""Verity Auth Module.

Default auth for this MVP is opaque session tokens validated via Redis.

Auth is evolving toward short-lived JWT access tokens issued by FastAPI.
To stay backwards-compatible, we accept JWTs first and fall back to Redis
session tokens.
"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from verity.auth.jwt_access import create_access_token
from verity.auth.jwt_access import get_current_user as _get_current_user_jwt
from verity.auth.jwt_access import get_optional_user as _get_optional_user_jwt
from verity.auth.redis_session import get_current_user as _get_current_user_redis
from verity.auth.redis_session import get_optional_user as _get_optional_user_redis
from verity.auth.supabase import verify_jwt
from verity.auth.schemas import TokenPayload, User
from verity.config import Settings, get_settings
from verity.exceptions import UnauthorizedException


security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """Default auth dependency.

    - Prefer FastAPI-issued JWT access tokens (no Redis dependency)
    - Fallback to legacy opaque session tokens stored in Redis
    """

    try:
        return await _get_current_user_jwt(request, credentials, settings)
    except UnauthorizedException:
        return await _get_current_user_redis(request, credentials, settings)


async def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User | None:
    user = await _get_optional_user_jwt(request, credentials, settings)
    if user is not None:
        return user
    return await _get_optional_user_redis(request, credentials, settings)

__all__ = [
    "get_current_user",
    "get_optional_user",
    "create_access_token",
    "verify_jwt",
    "TokenPayload",
    "User",
]
