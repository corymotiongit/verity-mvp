"""
Verity - Dependency Injection.

FastAPI dependencies for auth, feature flags, database, and services.
"""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, Header

from verity.config import FeatureFlags, Settings, get_settings
from verity.exceptions import FeatureDisabledException, ForbiddenException


# =============================================================================
# Settings Dependencies
# =============================================================================


def get_features(settings: Annotated[Settings, Depends(get_settings)]) -> FeatureFlags:
    """Get feature flags from settings."""
    return settings.features


# =============================================================================
# Request Context
# =============================================================================


def get_request_id(x_request_id: Annotated[str | None, Header()] = None) -> UUID:
    """Get or generate request ID for tracing."""
    if x_request_id:
        try:
            return UUID(x_request_id)
        except ValueError:
            pass
    return uuid4()


# =============================================================================
# Feature Flag Guards
# =============================================================================


def require_feature(feature_name: str):
    """Create a dependency that requires a specific feature to be enabled."""

    def check_feature(features: Annotated[FeatureFlags, Depends(get_features)]) -> bool:
        if not getattr(features, feature_name, False):
            raise FeatureDisabledException(feature_name)
        return True

    return check_feature


# Specific feature guards
require_documents = Depends(require_feature("documents"))
require_approvals = Depends(require_feature("approvals"))
require_agent = Depends(require_feature("agent"))
require_reports = Depends(require_feature("reports"))
require_charts = Depends(require_feature("charts"))
require_forecast = Depends(require_feature("forecast"))
require_logs = Depends(require_feature("logs"))
require_audit = Depends(require_feature("audit"))


# =============================================================================
# Role Guards
# =============================================================================


def require_role(*allowed_roles: str):
    """Create a dependency that requires specific roles."""

    from verity.auth import get_current_user
    from verity.auth.schemas import User

    async def check_role(user: Annotated[User, Depends(get_current_user)]) -> bool:
        roles = set(user.roles or ["user"])
        is_admin = "admin" in roles or "owner" in roles
        allowed = set(allowed_roles)

        if allowed and not (is_admin or roles.intersection(allowed)):
            raise ForbiddenException(
                "Insufficient permissions",
                required_role=", ".join(allowed_roles),
            )

        return True

    return Depends(check_role)


require_admin = require_role("admin")
require_approver = require_role("admin", "approver")
require_auditor = require_role("admin", "auditor")
