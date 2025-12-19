"""
Verity Agent - Router.

API endpoints for Veri agent.
Supports multi-organization isolation.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends

from verity.auth import get_current_user
from verity.auth.schemas import User
from verity.deps import require_agent
from verity.modules.agent.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    ConversationListResponse,
    ConversationResponse,
)
from verity.modules.agent.service import AgentService
from verity.schemas import PaginationMeta

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    dependencies=[require_agent],
)


def get_service() -> AgentService:
    """Get agent service instance."""
    return AgentService()


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(request: AgentChatRequest, user: User = Depends(get_current_user)):
    """
    Chat with Veri agent.
    
    - Uses org's File Search store for grounding
    - NEVER writes to DB, only proposes changes
    - Returns sources for all information
    - Returns chart_spec ONLY when explicitly requested
    """
    service = get_service()
    request_id = uuid4()
    return await service.chat(request, user, request_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: UUID, user: User = Depends(get_current_user)):
    """Get conversation history."""
    service = get_service()
    return await service.get_conversation(conversation_id, user)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user: User = Depends(get_current_user),
    page_size: int = 20,
    page_token: str | None = None,
):
    """List user's conversations."""
    service = get_service()
    items, next_token, total = await service.list_conversations(
        user, page_size, page_token
    )
    return ConversationListResponse(
        items=items,
        meta=PaginationMeta(
            total_count=total,
            page_size=page_size,
            next_page_token=next_token,
            has_more=next_token is not None,
        ),
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: UUID, user: User = Depends(get_current_user)):
    """Delete a conversation."""
    service = get_service()
    await service.delete_conversation(conversation_id, user)
    return None


# =============================================================================
# Chat Scope Management
# =============================================================================

from verity.modules.agent.schemas import ChatScope, ResolvedScope

@router.get("/chat/{conversation_id}/scope", response_model=ChatScope | None)
async def get_chat_scope(conversation_id: UUID, user: User = Depends(get_current_user)):
    """Get the active scope for a chat."""
    service = get_service()
    return await service.get_scope(conversation_id)


@router.put("/chat/{conversation_id}/scope", response_model=ChatScope)
async def update_chat_scope(conversation_id: UUID, scope: ChatScope, user: User = Depends(get_current_user)):
    """Update active scope for a chat."""
    service = get_service()
    return await service.update_scope(conversation_id, scope, user)


@router.post("/chat/{conversation_id}/scope/clear", status_code=204)
async def clear_chat_scope(conversation_id: UUID, user: User = Depends(get_current_user)):
    """Clear chat scope."""
    service = get_service()
    await service.clear_scope(conversation_id, user)


@router.post("/chat/{conversation_id}/scope/resolve", response_model=ResolvedScope)
async def resolve_chat_scope(conversation_id: UUID, user: User = Depends(get_current_user)):
    """Resolve the current scope into a list of documents effectively available."""
    service = get_service()
    from verity.modules.agent.scope_resolver import get_scope_resolver
    
    scope = await service.get_scope(conversation_id)
    if not scope:
        # Resolve empty/default
        scope = ChatScope(mode="empty")
        
    resolver = get_scope_resolver()
    return await resolver.resolve(scope, user)

