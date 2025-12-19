"""
Verity Agent - Schemas.

Pydantic models for agent/chat operations.
"""

from datetime import datetime
from typing import Any, Dict, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from verity.schemas import PaginationMeta


# =============================================================================
# Request Schemas
# =============================================================================


class ChatScope(BaseModel):
    """
    Persistent scope for a chat conversation.
    
    Defines what documents the agent can access during the conversation.
    If collection_id is set, it expands to the collection's filters.
    """
    
    # Filters (all are AND conditions)
    project: str | None = Field(default=None, description="Filter by project name")
    tag_ids: list[UUID] = Field(default_factory=list, description="Filter by tags (OR within tags)")
    category: str | None = Field(default=None, description="Filter by document category")
    period: str | None = Field(default=None, description="Filter by time period")
    source: str | None = Field(default=None, description="Filter by data source")
    
    # Explicit document selection (overrides filters if set)
    collection_id: UUID | None = Field(
        default=None, 
        description="Use a saved collection's filters (dominates over individual filters)"
    )
    doc_ids: list[UUID] = Field(
        default_factory=list, 
        description="Explicit document IDs (manual selection, ignores filters)"
    )
    
    # Mode
    mode: Literal["filtered", "all_docs", "empty"] = Field(
        default="filtered",
        description="'filtered' = use filters, 'all_docs' = no restrictions, 'empty' = force user to select"
    )


class ScopeSuggestion(BaseModel):
    """Actionable suggestion when scope is empty."""
    label: str = Field(..., description="Action text (e.g., 'Subir archivo')")
    action: Literal["upload", "clear_filters", "select_all", "select_project"]
    project_id: str | None = None


class ResolvedScope(BaseModel):
    """Result of resolving a ChatScope to actual document IDs."""
    
    doc_ids: list[UUID] = Field(default_factory=list, description="Final resolved document IDs")
    doc_count: int = Field(default=0, description="Total documents in scope")
    canonical_file_ids: list[UUID] = Field(default_factory=list, description="For tabular files")
    
    # Display info for UI
    display_summary: str = Field(default="", description="Human-readable scope summary")
    project: str | None = None
    tag_names: list[str] = Field(default_factory=list)
    collection_name: str | None = None
    
    # Validation / Diagnostics
    is_empty: bool = Field(default=False, description="True if no documents match scope")
    requires_action: bool = Field(default=False, description="True if user must specify scope")
    
    # Diagnostic info (when empty)
    empty_reason: str | None = Field(default=None, description="Why is it empty? (e.g., 'Project empty')")
    suggestion: ScopeSuggestion | None = Field(default=None, description="Suggested action")


class ChatContext(BaseModel):
    """Additional context for the agent request."""

    # Main scope (persistent per conversation)
    scope: ChatScope | None = Field(
        default=None,
        description="Document scope for this conversation"
    )
    
    # Legacy/convenience fields (override scope for single request)
    document_id: UUID | None = Field(
        default=None,
        description="Force query to use this specific document (bypasses scope)"
    )
    document_ids: list[UUID] | None = None
    include_db_context: bool = True
    document_category: str | None = Field(
        default=None,
        description="Legacy: filter by category"
    )
    document_project: str | None = Field(
        default=None,
        description="Legacy: filter by project"
    )


class AgentChatRequest(BaseModel):
    """Request to chat with Veri agent."""

    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: UUID | None = Field(
        default=None, description="Continue existing conversation"
    )
    context: ChatContext | None = None


# =============================================================================
# Response Schemas
# =============================================================================


class ValueInfo(BaseModel):
    """Structured value with type and formatting for audit."""
    
    value_type: Literal["number", "text", "date", "boolean", "list"] = "text"
    raw_value: Any = Field(..., description="Original value from data")
    formatted: str | None = Field(default=None, description="Human-readable format")
    unit: str | None = Field(default=None, description="Unit if applicable (e.g., MXN, USD, kg)")


class DataEvidence(BaseModel):
    """
    Evidence for tabular data queries (audit-ready).
    
    CRITICAL: row_ids is REQUIRED for audit. If missing, response should be blocked.
    """
    
    operation: Literal[
        "lookup",
        "aggregate",
        "aggregate_sum",
        "aggregate_mean",
        "group_aggregate",
        "filter",
        "count",
        "list",
        "query",
        "forecast",
    ] = Field(
        ..., description="Type of data operation performed"
    )
    match_policy: Literal["first", "all", "error_if_multiple"] = Field(
        default="all", description="How multiple matches are handled"
    )
    
    # Filters
    filter_applied: str | None = Field(default=None, description="e.g., PRODUCTO = 'Laptop Dell'")
    columns_used: list[str] = Field(default_factory=list, description="Columns involved in query")
    
    # Row Evidence (REQUIRED for audit)
    row_ids: list[int] = Field(
        default_factory=list, 
        description="Line numbers in canonical file (1-indexed). REQUIRED."
    )
    row_count: int = Field(default=0, description="Total matching rows")
    row_limit: int | None = Field(default=None, description="If truncated, what limit was applied")
    
    # Sample Rows (1-3 for visual audit)
    sample_rows: list[dict[str, Any]] = Field(
        default_factory=list, 
        description="1-3 sample rows with only columns_used (redacted)"
    )
    
    # Value Info (for scalar results)
    result_value: ValueInfo | None = Field(default=None, description="Structured result value")


class DocEvidence(BaseModel):
    """Evidence for document queries."""
    
    page: int | None = None
    section: str | None = None
    excerpt: str | None = Field(default=None, max_length=500)


class Source(BaseModel):
    """
    Unified source contract for all query types.
    
    - Tabular (type="data"): file, canonical_file_id, evidence=DataEvidence
    - DocQA (type="doc"): file, evidence=DocEvidence
    """

    type: Literal["data", "doc", "web"] = Field(
        ..., description="'data' for tabular, 'doc' for PDF/text"
    )
    file: str | None = Field(default=None, description="Filename for reference")
    canonical_file_id: str | None = Field(default=None, description="UUID of canonical file (tabular only)")
    
    # Structured evidence (replaces raw code snippet)
    data_evidence: DataEvidence | None = Field(default=None, description="For type='data'")
    doc_evidence: DocEvidence | None = Field(default=None, description="For type='doc'")
    
    # Legacy fields (for backwards compatibility)
    id: str | None = None
    title: str | None = None
    snippet: str | None = Field(default=None, description="DEPRECATED: Use evidence instead")
    relevance: float | None = None


class ProposedChange(BaseModel):
    """Agent-proposed change (never writes directly to DB)."""

    entity_type: str
    entity_id: UUID | None = None
    action: Literal["create", "update", "delete"]
    changes: dict[str, Any]
    requires_approval: bool = True


class ChartSpec(BaseModel):
    """Chart specification (only when explicitly requested)."""

    type: Literal["vega-lite", "chartjs", "plotly"]
    spec: dict[str, Any]


class MessageContent(BaseModel):
    """Message content."""

    role: Literal["user", "assistant"]
    content: str


class AgentChatResponse(BaseModel):
    """Response from Veri agent."""

    request_id: UUID = Field(..., description="Unique request ID for tracing")
    conversation_id: UUID
    message: MessageContent
    sources: list[Source] = Field(
        default_factory=list, description="Always included - citations"
    )
    proposed_changes: list[ProposedChange] | None = Field(
        default=None, description="Agent NEVER writes to DB, only proposes"
    )
    chart_spec: ChartSpec | None = Field(
        default=None, description="Only when user EXPLICITLY requests a chart"
    )
    table_preview: Dict[str, Any] | None = None
    evidence_ref: str | None = None
    scope_info: dict | None = Field(
        default=None, description="Information about active search scope (docs, filters)"
    )


# =============================================================================
# Conversation Schemas
# =============================================================================


class ConversationMessage(BaseModel):
    """Single message in conversation history."""

    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    request_id: UUID | None = None
    sources: list[Source] | None = None
    chart_spec: ChartSpec | None = None
    table_preview: Dict[str, Any] | None = None
    evidence_ref: str | None = None


class ConversationResponse(BaseModel):
    """Full conversation with messages."""

    id: UUID
    title: str | None = None
    messages: list[ConversationMessage]
    created_at: datetime
    updated_at: datetime | None = None


class ConversationSummary(BaseModel):
    """Conversation summary for listing."""

    id: UUID
    title: str | None = None
    message_count: int
    created_at: datetime
    updated_at: datetime | None = None


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""

    items: list[ConversationSummary]
    meta: PaginationMeta
