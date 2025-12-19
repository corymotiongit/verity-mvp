"""Verity Auth Module.

Default auth for this MVP is opaque session tokens validated via Redis.
"""

from verity.auth.redis_session import get_current_user, get_optional_user
from verity.auth.supabase import verify_jwt
from verity.auth.schemas import TokenPayload, User

__all__ = [
    "get_current_user",
    "get_optional_user",
    "verify_jwt",
    "TokenPayload",
    "User",
]
