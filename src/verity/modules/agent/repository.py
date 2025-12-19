"""
Verity Agent - Repository.

Database operations for conversations.
"""

from typing import Any
from uuid import UUID

from verity.core.repository import BaseRepository


class ConversationsRepository(BaseRepository[dict[str, Any]]):
    """Repository for conversations in Supabase."""

    @property
    def table_name(self) -> str:
        return "conversations"

    async def list_by_user(
        self,
        user_id: UUID,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """List conversations for a specific user."""
        return await self.list(
            page_size=page_size,
            page_token=page_token,
            filters={"user_id": str(user_id)},
        )

    async def add_message(
        self,
        conversation_id: UUID,
        message: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a message to a conversation."""
        conversation = await self.get_by_id_or_raise(conversation_id)
        messages = conversation.get("messages", [])
        messages.append(message)

        return await self.update(
            conversation_id,
            {
                "messages": messages,
                "message_count": len(messages),
            },
        )

    async def update_title(
        self,
        conversation_id: UUID,
        title: str,
    ) -> dict[str, Any]:
        """Update conversation title."""
        return await self.update(conversation_id, {"title": title})
