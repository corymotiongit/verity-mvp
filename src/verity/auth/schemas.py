"""
Verity Auth - Schemas.

Pydantic models for authentication with multi-organization support.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """JWT token payload from Supabase."""

    sub: str = Field(..., description="User ID (UUID string)")
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    aud: str | None = None
    exp: int | None = None
    iat: int | None = None


class Organization(BaseModel):
    """Organization model."""

    id: UUID
    name: str
    slug: str
    file_search_store_id: str | None = None
    settings: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class User(BaseModel):
    """Authenticated user with organization context."""

    id: UUID
    email: str | None = None
    org_id: UUID
    organization: Organization | None = None
    display_name: str | None = None
    roles: list[str] = Field(default_factory=lambda: ["user"])

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return "admin" in self.roles or "owner" in self.roles

    @property
    def is_approver(self) -> bool:
        """Check if user can approve changes."""
        return "approver" in self.roles or self.is_admin

    @property
    def is_auditor(self) -> bool:
        """Check if user can view audit logs."""
        return "auditor" in self.roles or self.is_admin

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles or self.is_admin


class UserRole(BaseModel):
    """User role assignment."""

    user_id: UUID
    role: Literal["user", "approver", "auditor", "admin", "owner"]
    created_at: datetime | None = None
