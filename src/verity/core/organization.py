"""
Verity Core - Organization Repository.

Database operations for organizations.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from verity.core.supabase_client import get_supabase_client
from verity.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class OrganizationRepository:
    """Repository for organization operations."""

    def __init__(self):
        self.table = "organizations"

    async def get_by_id(self, org_id: UUID) -> dict[str, Any] | None:
        """Get organization by ID."""
        client = get_supabase_client()
        
        result = client.table(self.table).select("*").eq("id", str(org_id)).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None

    async def get_by_id_or_raise(self, org_id: UUID) -> dict[str, Any]:
        """Get organization by ID or raise NotFoundException."""
        org = await self.get_by_id(org_id)
        if not org:
            raise NotFoundException("organization", org_id)
        return org

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new organization."""
        client = get_supabase_client()
        
        result = client.table(self.table).insert(data).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        raise Exception("Failed to create organization")

    async def update_file_search_store(
        self, org_id: UUID, store_name: str
    ) -> dict[str, Any]:
        """Update organization's File Search store ID."""
        client = get_supabase_client()
        
        result = (
            client.table(self.table)
            .update({
                "file_search_store_id": store_name,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(org_id))
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        raise NotFoundException("organization", org_id)


class ProfileRepository:
    """Repository for user profiles."""

    def __init__(self):
        self.table = "profiles"

    async def get_by_user_id(self, user_id: UUID) -> dict[str, Any] | None:
        """Get profile by user ID."""
        client = get_supabase_client()
        
        result = (
            client.table(self.table)
            .select("*, organizations(*)")
            .eq("id", str(user_id))
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new profile."""
        client = get_supabase_client()
        
        result = client.table(self.table).insert(data).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        raise Exception("Failed to create profile")


class UserRolesRepository:
    """Repository for user roles."""

    def __init__(self):
        self.table = "user_roles"

    async def get_roles_for_user(self, user_id: UUID) -> list[str]:
        """Get all roles for a user."""
        client = get_supabase_client()
        
        result = (
            client.table(self.table)
            .select("role")
            .eq("user_id", str(user_id))
            .execute()
        )
        
        return [r["role"] for r in result.data] if result.data else []

    async def add_role(self, user_id: UUID, role: str) -> None:
        """Add a role to a user."""
        client = get_supabase_client()
        
        client.table(self.table).insert({
            "user_id": str(user_id),
            "role": role,
        }).execute()
