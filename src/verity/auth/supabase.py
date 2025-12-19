"""
Verity Auth - Supabase JWT Validation.

Validates JWT tokens issued by Supabase Auth.
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from verity.auth.schemas import TokenPayload, User
from verity.config import Settings, get_settings
from verity.exceptions import UnauthorizedException

# Security scheme
security = HTTPBearer(auto_error=False)


def verify_jwt(
    token: str,
    secret: str,
    algorithms: list[str] | None = None,
) -> TokenPayload:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token string
        secret: The secret key for verification
        algorithms: List of allowed algorithms (default: HS256)

    Returns:
        Decoded token payload

    Raises:
        UnauthorizedException: If token is invalid or expired
    """
    if algorithms is None:
        algorithms = ["HS256"]

    try:
        payload = jwt.decode(token, secret, algorithms=algorithms)

        # Validate expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
            raise UnauthorizedException("Token has expired")

        return TokenPayload(
            sub=UUID(payload["sub"]),
            email=payload.get("email"),
            role=payload.get("role", payload.get("user_role", "user")),
            aud=payload.get("aud"),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        )
    except JWTError as e:
        raise UnauthorizedException(f"Invalid token: {e}")
    except (KeyError, ValueError) as e:
        raise UnauthorizedException(f"Malformed token payload: {e}")


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """
    Get the current authenticated user from the request.

    This is a FastAPI dependency that extracts and validates the JWT
    from the Authorization header.

    Returns:
        Authenticated User object

    Raises:
        UnauthorizedException: If no token or invalid token
    """
    if not credentials:
        raise UnauthorizedException("Missing authentication token")

    token_payload = verify_jwt(
        token=credentials.credentials,
        secret=settings.supabase.jwt_secret,
    )

    user = User(
        id=token_payload.sub,
        email=token_payload.email,
        role=token_payload.role,  # type: ignore
    )

    # Store user in request state for access in other dependencies
    request.state.user = user.model_dump()

    return user


async def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User | None:
    """
    Get the current user if authenticated, otherwise None.

    Useful for endpoints that work for both authenticated and anonymous users.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(request, credentials, settings)
    except UnauthorizedException:
        return None
