"""
Verity Core - Base Repository.

Abstract base class for all repositories following the repository pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from supabase import Client

from verity.core.supabase_client import get_supabase_client
from verity.exceptions import NotFoundException

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository for database operations.

    All module repositories should inherit from this class.
    """

    def __init__(self, client: Client | None = None):
        """Initialize repository with optional Supabase client."""
        self._client = client or get_supabase_client()

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Return the table name for this repository."""
        ...

    @property
    def table(self):
        """Get the Supabase table reference."""
        return self._client.table(self.table_name)

    async def get_by_id(self, id: UUID) -> T | None:
        """
        Get a single record by ID.

        Args:
            id: The record UUID

        Returns:
            The record if found, None otherwise
        """
        response = self.table.select("*").eq("id", str(id)).maybe_single().execute()
        return response.data

    async def get_by_id_or_raise(self, id: UUID) -> T:
        """
        Get a single record by ID, raise if not found.

        Args:
            id: The record UUID

        Returns:
            The record

        Raises:
            NotFoundException: If record not found
        """
        result = await self.get_by_id(id)
        if not result:
            raise NotFoundException(self.table_name, id)
        return result

    async def list(
        self,
        page_size: int = 20,
        page_token: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[T], str | None]:
        """
        List records with pagination.

        Args:
            page_size: Number of records per page
            page_token: Token for next page (offset as string)
            filters: Optional filters to apply

        Returns:
            Tuple of (records, next_page_token)
        """
        offset = int(page_token) if page_token else 0

        query = self.table.select("*", count="exact")

        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        response = (
            query.order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        items = response.data or []
        total = response.count or 0

        next_token = None
        if offset + len(items) < total:
            next_token = str(offset + page_size)

        return items, next_token

    async def create(self, data: dict[str, Any]) -> T:
        """
        Create a new record.

        Args:
            data: The record data

        Returns:
            The created record
        """
        response = self.table.insert(data).execute()
        return response.data[0]

    async def update(self, id: UUID, data: dict[str, Any]) -> T:
        """
        Update an existing record.

        Args:
            id: The record UUID
            data: The update data

        Returns:
            The updated record
        """
        response = self.table.update(data).eq("id", str(id)).execute()
        if not response.data:
            raise NotFoundException(self.table_name, id)
        return response.data[0]

    async def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.

        Args:
            id: The record UUID

        Returns:
            True if deleted
        """
        self.table.delete().eq("id", str(id)).execute()
        return True
