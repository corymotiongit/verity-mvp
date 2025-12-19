"""
Verity Agent - Veri Orchestrator.

Central logic that coordinates specialized agents:
1. DocQA: For semantic search on PDFs/Text (using File Search).
2. DataQuery: For deterministic analysis on CSV/Excel (using Pandas).

Refactored from monolithic AgentService.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, List, Dict, Tuple
from uuid import UUID, uuid4
from pathlib import Path

from google import genai
from google.genai import types

from verity.auth.schemas import User
from verity.core.gemini import get_gemini_client
from verity.exceptions import ExternalServiceException, NotFoundException
from verity.modules.agent.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    ChartSpec,
    ConversationMessage,
    ConversationResponse,
    ConversationSummary,
    MessageContent,
    ProposedChange,
    Source,
)

# Sub-Agents
from verity.modules.agent.doc_qa import DocQAAgent
from verity.modules.data import get_data_engine, DataEngineResponse
from verity.modules.data.schemas import TablePreview
from verity.modules.documents.service import DocumentsService # To get file list

logger = logging.getLogger(__name__)

# In-memory conversation storage (replace with DB in production)
_conversations: dict[str, dict[str, Any]] = {}

# Persist conversations to disk for MVP so they survive server restarts/reload.
# This keeps frontend chat history stable even when uvicorn reloads.
CONVERSATIONS_PATH = Path("uploads/conversations.json")


def _coerce_model_to_dict(value: Any) -> Any:
    """Convert Pydantic models (and similar) into plain JSON-serializable dicts."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return value
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            pass
    return value


def _coerce_table_preview_dict(value: Any) -> dict[str, Any] | None:
    """Return a dict table_preview shape {columns, rows, total_rows} if possible."""
    value = _coerce_model_to_dict(value)
    if not isinstance(value, dict):
        return None
    cols = value.get("columns")
    rows = value.get("rows")
    if not isinstance(cols, list) or not isinstance(rows, list):
        return None
    return value


def _load_conversations() -> None:
    global _conversations
    if not CONVERSATIONS_PATH.exists():
        return
    try:
        with open(CONVERSATIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            _conversations = data
    except Exception as e:
        logger.error(f"Failed to load conversations: {e}")


def _save_conversations() -> None:
    try:
        CONVERSATIONS_PATH.parent.mkdir(exist_ok=True)
        tmp_path = CONVERSATIONS_PATH.with_suffix(CONVERSATIONS_PATH.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(_conversations, f, indent=2, default=str, ensure_ascii=False)
        tmp_path.replace(CONVERSATIONS_PATH)
    except Exception as e:
        logger.error(f"Failed to save conversations: {e}")

# Context/Scope storage: {conversation_id: ChatScope_dict}
_chat_contexts: dict[str, dict] = {}
CHAT_CONTEXT_PATH = Path("uploads/chat_contexts.json")

def _load_chat_contexts():
    global _chat_contexts
    if CHAT_CONTEXT_PATH.exists():
        try:
            with open(CHAT_CONTEXT_PATH) as f:
                _chat_contexts = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load chat contexts: {e}")

def _save_chat_contexts():
    CHAT_CONTEXT_PATH.parent.mkdir(exist_ok=True)
    with open(CHAT_CONTEXT_PATH, "w") as f:
        json.dump(_chat_contexts, f, indent=2, default=str)

_load_chat_contexts()

_load_conversations()

# Org stores cache
from verity.modules.documents.service import _org_stores

CHART_KEYWORDS = [
    "grafico", "chart", "visualiza", "plot", "diagrama",
    "muestra en grafico", "dibuja", "grafica", "pie chart",
    "bar chart", "line chart", "scatter", "histogram",
]

ORCHESTRATOR_SYSTEM_PROMPT = """You are Veri Orchestrator.
Your job is to route the user's question to the correct specialist or answer directly if it's general chat.

Available Specialists:
1. "data_query": For questions about TABULAR data (numbers, filtered lists, aggregations) on CSV/Excel files.
2. "doc_qa": For questions about TEXT/PDF documents (policies, contracts, summaries).

Input Context:
- User Question
- Available Files (Filename, Type)

Output JSON:
{
  "intent": "data_query" | "doc_qa" | "general_chat",
  "target_file_id": "string (UUID)" (Required if intent is data_query, best guess from context),
  "reasoning": "string"
}

Rules:
- If user asks about numbers like "how many", "sum", "average", "list projects in X" -> PREFER data_query.
- If user uses pronouns ("su", "él", "ella", "del mismo", "y del X") likely referring to a previous data entity -> PREFER data_query (target the same file).
- If user asks about "who is", "what is the policy", "summarize content" -> PREFER doc_qa.
- If user asks to "plot", "chart", "graph", "visualize", "show distribution" -> PREFER data_query (to get the data).
- If user greets or says thanks -> general_chat.
"""

class AgentService:
    """
    Veri Orchestrator Service.
    Replaces the old monolithic logic.
    """

    def __init__(self):
        self.doc_qa = DocQAAgent()
        self.data_engine = get_data_engine()
        self.doc_service = DocumentsService()
        self.gemini_client = get_gemini_client()
        self.model = "gemini-2.0-flash-exp"

    def _get_org_store(self, user: User, project: str | None = None) -> str | None:
        """Wrapper for existing store logic (legacy needed for DocQA)."""
        # Reuse logic from doc service wrapper if needed, or implement here.
        # Implemented inline for simplicity to match previous behavior
        org_id = str(user.org_id)
        store_key = f"{org_id}:{project}" if project else org_id
        
        if store_key in _org_stores:
            return _org_stores[store_key]
        if project and org_id in _org_stores:
            return _org_stores[org_id]
        if user.organization and user.organization.file_search_store_id:
            store_name = user.organization.file_search_store_id
            _org_stores[org_id] = store_name
            return store_name
        return None

    # -------------------------------------------------------------------------
    # Context/Scope Management
    # -------------------------------------------------------------------------

    async def get_scope(self, conversation_id: UUID) -> Any:
        """Get the current scope for a conversation."""
        cid_str = str(conversation_id)
        if cid_str in _chat_contexts:
            from verity.modules.agent.schemas import ChatScope
            return ChatScope(**_chat_contexts[cid_str])
        return None

    async def update_scope(self, conversation_id: UUID, scope: Any, user: User) -> Any:
        """Update (replace) scope for a conversation."""
        cid_str = str(conversation_id)
        
        # Log if changing
        old_scope = await self.get_scope(conversation_id)
        
        # Save
        _chat_contexts[cid_str] = scope.model_dump()
        _save_chat_contexts()
        
        # Audit
        # Audit
        from verity.modules.agent.scope_resolver import log_scope_change
        
        # log_scope_change expects ChatScope objects. Since we are in the service,
        # we can reconstruct them or pass as dicts if adjusted.
        # Ideally, audit should happen here. For MVP, reusing the simple log:
        log_scope_change(
            str(conversation_id),
            user,
            old_scope,
            scope
        )
        
        return scope

    async def clear_scope(self, conversation_id: UUID, user: User):
        """Clear scope for a conversation."""
        cid_str = str(conversation_id)
        if cid_str in _chat_contexts:
            del _chat_contexts[cid_str]
            _save_chat_contexts()
            

    async def chat(
        self,
        request: AgentChatRequest,
        user: User,
        request_id: UUID,
    ) -> AgentChatResponse:
        """Main Orchestrator Entry Point."""

        # Allows re-running a prior query in the same turn (e.g., after answering a pending setting).
        user_message = request.message
        
        # 1. Get Conversation
        conversation_id = request.conversation_id or uuid4()
        if str(conversation_id) not in _conversations:
            self._create_conversation(conversation_id, user)
        conversation = _conversations[str(conversation_id)]

        # 2. Add User Message to History
        now = datetime.now(timezone.utc)
        conversation["messages"].append({
            "role": "user",
            "content": request.message,
            "timestamp": now.isoformat(),
            "request_id": str(request_id),
        })

        # Persist user message immediately so reload/restart doesn't drop state
        conversation["message_count"] = len(conversation["messages"])
        conversation["updated_at"] = now.isoformat()
        if not conversation.get("title"):
            title = (request.message or "").strip()
            conversation["title"] = title[:50] if title else None
        _save_conversations()

        # 2.4 Pending forecast confidence choice (user replies with 80/95)
        pending_forecast = conversation.get("pending_forecast_confidence_choice")
        if pending_forecast:
            chosen_conf = self._parse_forecast_confidence_choice(request.message)
            if chosen_conf is not None:
                fs = conversation.get("forecast_settings") or {}
                fs["confidence"] = chosen_conf
                conversation["forecast_settings"] = fs

                # Mirror into chat_context for downstream guards/normalizers
                cid_str = str(conversation_id)
                ctx = _chat_contexts.get(cid_str) or {}
                fs_ctx = ctx.get("forecast_settings") or {}
                fs_ctx["confidence"] = chosen_conf
                ctx["forecast_settings"] = fs_ctx
                _chat_contexts[cid_str] = ctx
                _save_chat_contexts()

                conversation.pop("pending_forecast_confidence_choice", None)
                conversation["updated_at"] = datetime.now(timezone.utc).isoformat()
                _save_conversations()

                orig = pending_forecast.get("original_query")
                if isinstance(orig, str) and orig.strip():
                    user_message = orig

        # 2.5 Pending chart choice handling (user replies with 1/2/3)
        pending = conversation.get("pending_chart_choice")
        if pending:
            chosen_type = self._parse_chart_choice(request.message)
            if chosen_type:
                try:
                    chart_spec_wrapper, table_preview, evidence_ref = self._build_chart_from_pending(
                        pending=pending,
                        chosen_type=chosen_type,
                    )

                    pending_sources = []
                    for s in (pending.get("sources") or []):
                        try:
                            pending_sources.append(Source.model_validate(s))
                        except Exception:
                            # Keep going even if a legacy/invalid source slips in
                            continue

                    # Clear pending state
                    conversation.pop("pending_chart_choice", None)

                    assistant_text = (
                        f"Listo. Se generó la gráfica **{chosen_type}** con la última tabla."
                        "\n\nSi quieres cambiar el tipo, responde con 1-6: "
                        "1) Bar  2) Line  3) Scatter  4) Heatmap  5) Treemap  6) Stacked Bar."
                    )

                    # Enforce ANTI rules (FUENTES / audit / no-code) on this early-return path too.
                    try:
                        from verity.modules.agent.anti import anti_normalize

                        cid_str = str(conversation_id)
                        chat_ctx = dict(_chat_contexts.get(cid_str) or {})
                        if conversation.get("forecast_settings"):
                            fs = chat_ctx.get("forecast_settings") or {}
                            fs.update(conversation.get("forecast_settings") or {})
                            chat_ctx["forecast_settings"] = fs

                        assistant_text, _ = anti_normalize(
                            user_message=user_message,
                            chat_context=chat_ctx,
                            assistant_message=assistant_text,
                            sources=pending_sources,
                            data_meta={
                                "table_preview": table_preview,
                                "chart_spec": chart_spec_wrapper,
                                "evidence_ref": evidence_ref,
                            },
                        )
                    except Exception as e:
                        logger.warning(f"ANTI normalization failed (pending chart): {e}")

                    assistant_msg_dict = {
                        "role": "assistant",
                        "content": assistant_text,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "request_id": str(request_id),
                        "sources": [s.model_dump() for s in pending_sources],
                        "chart_spec": chart_spec_wrapper,
                        "table_preview": table_preview,
                        "evidence_ref": evidence_ref,
                    }

                    conversation["messages"].append(assistant_msg_dict)
                    conversation["message_count"] = len(conversation["messages"])
                    conversation["updated_at"] = datetime.now(timezone.utc).isoformat()
                    if not conversation.get("title"):
                        conversation["title"] = request.message[:50]

                    _save_conversations()

                    return AgentChatResponse(
                        request_id=request_id,
                        conversation_id=conversation_id,
                        message=MessageContent(role="assistant", content=assistant_text),
                        sources=pending_sources,
                        proposed_changes=None,
                        scope_info=None,
                        chart_spec=chart_spec_wrapper,
                        table_preview=table_preview,
                        evidence_ref=evidence_ref,
                    )
                except ValueError as e:
                    # Keep pending state so user can choose another option
                    assistant_text = (
                        f"No puedo generar **{chosen_type}** con esta tabla: {str(e)}.\n\n"
                        "Elige otra opción (1-6): 1) Bar  2) Line  3) Scatter  4) Heatmap  5) Treemap  6) Stacked Bar."
                    )

                    assistant_msg_dict = {
                        "role": "assistant",
                        "content": assistant_text,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "request_id": str(request_id),
                        "sources": [],
                    }
                    conversation["messages"].append(assistant_msg_dict)
                    conversation["message_count"] = len(conversation["messages"])
                    conversation["updated_at"] = datetime.now(timezone.utc).isoformat()

                    _save_conversations()

                    return AgentChatResponse(
                        request_id=request_id,
                        conversation_id=conversation_id,
                        message=MessageContent(role="assistant", content=assistant_text),
                        sources=[],
                        proposed_changes=None,
                        scope_info=None,
                        chart_spec=None,
                        table_preview=None,
                        evidence_ref=None,
                    )
                except Exception as e:
                    logger.warning(f"Pending chart choice failed, falling back: {e}")

        # 2.6 Chart follow-up shortcut (e.g., "grafícalo") BEFORE intent routing
        # This avoids misclassification to the wrong dataset and prevents a new DataEngine query.
        try:
            user_text = (request.message or "").strip()
            user_text_l = user_text.lower()
            chart_triggers = [
                "grafica",
                "gráfica",
                "grafic",
                "graficalo",
                "graficarlo",
                "grafícalo",
                "graficar",
                "chart",
                "plot",
                "visuali",
                "dibuja",
                "pintar",
                "haz una grafica",
                "haz una gráfica",
                "muestralo en grafica",
                "muéstralo en gráfica",
            ]
            should_chart_followup = any(k in user_text_l for k in chart_triggers) and len(user_text.split()) <= 3

            if should_chart_followup and conversation.get("messages"):
                last_tp: dict[str, Any] | None = None
                last_sources_raw: list[dict[str, Any]] = []
                last_evidence_ref: str | None = None

                for msg in reversed(conversation["messages"]):
                    if msg.get("role") != "assistant":
                        continue
                    tp = _coerce_table_preview_dict(msg.get("table_preview"))
                    if tp and tp.get("rows"):
                        last_tp = tp
                        last_sources_raw = msg.get("sources") or []
                        last_evidence_ref = msg.get("evidence_ref")
                        break

                if last_tp:
                    logger.info("[CHAT] SHORTCUT ACTIVATED: chart choice for last table")

                    import pandas as pd

                    df_prev = pd.DataFrame(last_tp["rows"], columns=last_tp["columns"])
                    try:
                        table_md = df_prev.head(10).to_markdown(index=False)
                    except ImportError:
                        table_md = df_prev.head(10).to_string(index=False)

                    conversation["pending_chart_choice"] = {
                        "table_preview": last_tp,
                        "evidence_ref": last_evidence_ref or "Contexto histórico",
                        "sources": last_sources_raw,
                        "original_query": user_text,
                    }

                    x_field, y_field = self._infer_xy_fields(last_tp)
                    series_field = self._infer_series_field(last_tp, x_field, y_field)
                    recommendation = self._recommend_chart_type(last_tp, x_field, y_field, series_field)

                    assistant_text = (
                        "Se encontró la **última tabla** en el historial.\n\n"
                        f"{table_md}\n\n"
                        "¿Qué tipo de gráfica prefieres?\n"
                        "1) Bar\n"
                        "2) Line\n"
                        "3) Scatter\n"
                        "4) Heatmap\n"
                        "5) Treemap\n\n"
                        "6) Stacked Bar\n\n"
                        f"Recomendación: **{recommendation}**. Responde con 1-6."
                    )

                    pending_sources: list[Source] = []
                    for s in last_sources_raw:
                        try:
                            pending_sources.append(Source.model_validate(s))
                        except Exception:
                            continue

                    assistant_msg_dict = {
                        "role": "assistant",
                        "content": assistant_text,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "request_id": str(request_id),
                        "sources": [s.model_dump() for s in pending_sources],
                        "table_preview": last_tp,
                        "chart_spec": None,
                        "evidence_ref": last_evidence_ref,
                    }

                    conversation["messages"].append(assistant_msg_dict)
                    conversation["message_count"] = len(conversation["messages"])
                    conversation["updated_at"] = datetime.now(timezone.utc).isoformat()
                    _save_conversations()

                    return AgentChatResponse(
                        request_id=request_id,
                        conversation_id=conversation_id,
                        message=MessageContent(role="assistant", content=assistant_text),
                        sources=pending_sources,
                        proposed_changes=None,
                        scope_info=None,
                        chart_spec=None,
                        table_preview=last_tp,
                        evidence_ref=last_evidence_ref,
                    )
        except Exception as e:
            logger.warning(f"[CHAT] Chart follow-up shortcut failed: {e}")

        # 3. Resolve Scope (persistent per conversation)
        from verity.modules.agent.scope_resolver import get_scope_resolver
        from verity.modules.agent.schemas import ChatScope, ResolvedScope
        
        scope_resolver = get_scope_resolver()
        active_scope: ChatScope | None = None
        
        # A. If scope provided in request -> Update persistent scope
        if request.context and request.context.scope:
            active_scope = request.context.scope
            await self.update_scope(conversation_id, active_scope, user)
        # B. Else -> Use persistent scope
        else:
            active_scope = await self.get_scope(conversation_id)
            
        resolved_scope: ResolvedScope | None = None
        
        if active_scope:
            resolved_scope = await scope_resolver.resolve(active_scope, user)
            
            # Log scope info
            logger.info(
                f"[SCOPE] Resolved: {resolved_scope.display_summary}, "
                f"doc_count={resolved_scope.doc_count}, is_empty={resolved_scope.is_empty}"
            )
            
            # If scope requires action (empty mode), ask user
            if resolved_scope.requires_action and resolved_scope.is_empty:
                reason = resolved_scope.empty_reason or "No hay documentos en el scope actual."
                msg = f"🔍 {reason}\n\nPor favor:"
                
                if resolved_scope.suggestion:
                    msg += f"\n* **{resolved_scope.suggestion.label}**"
                
                msg += "\n* Selecciona un proyecto\n* Ajusta los filtros"
                
                return AgentChatResponse(
                    conversation_id=conversation_id,
                    message=MessageContent(
                        role="assistant",
                        content=msg
                    ),
                    sources=[],
                    scope_info={
                        "display": resolved_scope.display_summary,
                        "doc_count": 0,
                        "requires_action": True,
                        "empty_reason": resolved_scope.empty_reason,
                        "suggestion": resolved_scope.suggestion.model_dump() if resolved_scope.suggestion else None
                    }
                )


        # 4. Intent Classification (with scope awareness)
        ctx_category = request.context.document_category if request.context else None
        ctx_project = request.context.document_project if request.context else None
        forced_document_id = request.context.document_id if request.context else None
        
        # If scope has explicit doc, use it
        if resolved_scope and len(resolved_scope.doc_ids) == 1:
            forced_document_id = resolved_scope.doc_ids[0]
        
        if forced_document_id:
            # EXPLICIT document_id provided - bypass classification, force data_query
            intent = "data_query"
            target_file_id = str(forced_document_id)
            reasoning = "Forced by explicit document_id in context"
            logger.info(
                f"[ROUTING] FORCED: route_selected={intent}, "
                f"target_file_id={target_file_id} (context.document_id)"
            )
        else:
            # Normal classification flow (scope-aware)
            scope_project = resolved_scope.project if resolved_scope else None
            intent, target_file_id, reasoning = await self._classify_intent(
                query=user_message,
                user=user,
                category=ctx_category,
                project=scope_project or ctx_project,
                scope_doc_ids=resolved_scope.doc_ids if resolved_scope else None
            )
            logger.info(
                f"[ROUTING] route_selected={intent}, "
                f"target_file_id={target_file_id}, "
                f"reasoning={reasoning[:100] if reasoning else 'None'}"
            )

        # 5. Routing
        assistant_message = ""
        sources: List[Source] = []
        data_meta = None
        
        try:
            if intent == "data_query" and target_file_id:
                assistant_message, sources, data_meta = await self._handle_data_query(
                    query=user_message,
                    target_file_id=target_file_id,
                    user=user,
                    conversation_id=str(conversation_id)
                )
            elif intent == "doc_qa":
                # Determine store
                project = resolved_scope.project if resolved_scope else (request.context.document_project if request.context else None)
                store_name = self._get_org_store(user, project=project)
                category = request.context.document_category if request.context else None
                
                assistant_message, sources = await self._handle_doc_qa(
                    query=user_message,
                    store_name=store_name,
                    category=category
                )
            else:
                # General Chat
                # Fallback to simple generation without groundedness
                response = self.gemini_client.models.generate_content(
                    model=self.model,
                    contents=f"You are Veri, an AI assistant. User says: {user_message}"
                )
                assistant_message = response.text

        except Exception as e:
            logger.error(f"Error during orchestration: {e}")
            assistant_message = "Ocurrió un problema procesando la solicitud. Intenta de nuevo."

        # 5. ANTI normalization (guard/validator)
        try:
            from verity.modules.agent.anti import anti_normalize

            cid_str = str(conversation_id)
            chat_ctx = dict(_chat_contexts.get(cid_str) or {})
            if conversation.get("forecast_settings"):
                fs = chat_ctx.get("forecast_settings") or {}
                fs.update(conversation.get("forecast_settings") or {})
                chat_ctx["forecast_settings"] = fs

            assistant_message, data_meta = anti_normalize(
                user_message=user_message,
                chat_context=chat_ctx,
                assistant_message=assistant_message,
                sources=sources,
                data_meta=data_meta,
            )
        except Exception as e:
            logger.warning(f"ANTI normalization failed (skipping): {e}")

        # 6. Save & Respond
        clean_message = self._clean_response(assistant_message)
        
        # Build message dict with all fields for history/shortcut
        assistant_msg_dict = {
            "role": "assistant",
            "content": clean_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(request_id),
            "sources": [s.model_dump() for s in sources],
        }
        
        # Add data_meta fields for shortcut re-use (chart from last table)
        if data_meta:
            tp = _coerce_table_preview_dict(data_meta.get("table_preview"))
            if tp:
                assistant_msg_dict["table_preview"] = tp
            cs = _coerce_model_to_dict(data_meta.get("chart_spec"))
            if cs:
                assistant_msg_dict["chart_spec"] = cs
            ev = _coerce_model_to_dict(data_meta.get("evidence_ref"))
            if ev:
                assistant_msg_dict["evidence_ref"] = ev
        
        conversation["messages"].append(assistant_msg_dict)
        conversation["message_count"] = len(conversation["messages"])
        conversation["updated_at"] = datetime.now(timezone.utc).isoformat()
        if not conversation["title"]:
            conversation["title"] = user_message[:50]

        _save_conversations()

        # Prepare scope info for UI banner
        ui_scope_info = None
        if resolved_scope:
            ui_scope_info = {
                "display": resolved_scope.display_summary,
                "doc_count": resolved_scope.doc_count,
                "requires_action": resolved_scope.requires_action
            }

        return AgentChatResponse(
            request_id=request_id,
            conversation_id=conversation_id,
            message=MessageContent(role="assistant", content=clean_message),
            sources=sources,
            proposed_changes=None,

            scope_info=ui_scope_info,
            chart_spec=data_meta.get("chart_spec") if data_meta else None,
            table_preview=data_meta.get("table_preview") if data_meta else None,
            evidence_ref=data_meta.get("evidence_ref") if data_meta else None
        )

    async def _classify_intent(
        self, 
        query: str, 
        user: User,
        category: str | None = None,
        project: str | None = None,
        scope_doc_ids: List[UUID] | None = None
    ) -> Tuple[str, str | None, str]:
        """Classify user intent and identify target file using Gemini.
        
        If category, project, or scope_doc_ids are provided, only documents matching
        those filters will be considered.
        """
        # Get simplified list of files
        docs, _, _ = await self.doc_service.list_documents(user, page_size=100)
        
        # Filter by scope (doc_ids), category, or project
        if category or project or scope_doc_ids:
            filtered_docs = []
            scope_str_ids = {str(uid) for uid in scope_doc_ids} if scope_doc_ids else None
            
            for d in docs:
                doc_meta = d.metadata or {}
                
                # Filter by Scope (specific doc IDs)
                if scope_str_ids and str(d.id) not in scope_str_ids:
                    continue
                
                # Filter by Category
                if category and doc_meta.get("category") != category:
                    continue
                
                # Filter by Project
                if project and doc_meta.get("project") != project:
                    continue
                    
                filtered_docs.append(d)
            
            docs = filtered_docs
            logger.info(f"Filtered to {len(docs)} docs with scope_ids={len(scope_str_ids) if scope_str_ids else 0}, category={category}, project={project}")
        
        file_list = []
        for d in docs:
            # Include metadata for better context
            meta_str = ""
            if d.metadata:
                if d.metadata.get("category"):
                    meta_str += f", category: {d.metadata['category']}"
                if d.metadata.get("project"):
                    meta_str += f", project: {d.metadata['project']}"
            file_list.append(f"ID: {d.id}, Name: {d.display_name} ({d.mime_type}{meta_str})")
        
        logger.info(f"Classifying intent with files: {file_list}")
        
        context = f"""
        User Question: "{query}"
        Available Files:
        {json.dumps(file_list, indent=2)}
        """
        
        try:
            response = self.gemini_client.models.generate_content(
                model=self.model,
                contents=ORCHESTRATOR_SYSTEM_PROMPT + "\n\n" + context,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text)
            return data.get("intent", "general_chat"), data.get("target_file_id"), data.get("reasoning", "")
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return "general_chat", None, "Error"

    async def _handle_doc_qa(self, query: str, store_name: str, category: str = None) -> Tuple[str, List[Source]]:
        """Delegate to DocQA agent."""
        if not store_name:
            return "No tengo acceso a documentos en este momento.", []
            
        result = await self.doc_qa.answer(query, store_name, category)
        
        # Map sources with structured DocEvidence
        from verity.modules.agent.schemas import DocEvidence
        
        sources = []
        for src in result.get("sources", []):
            content = src.get("content") or ""
            
            doc_evidence = DocEvidence(
                page=src.get("page"),
                section=src.get("section"),
                excerpt=content[:500] if content else None
            )
            
            sources.append(Source(
                type="doc",  # New unified type
                file=src.get("title", "Document"),
                doc_evidence=doc_evidence,
                # Legacy fields
                id=str(uuid4()),
                title=src.get("title", "Doc"),
                relevance=src.get("relevance", 0.0)
            ))
            
        return result.get("answer", ""), sources

    def _get_entity_context(self, conversation_id: str) -> str:
        """Retrieve implicit entity context from previous turns."""
        ctx = _chat_contexts.get(str(conversation_id), {})
        last_id = ctx.get("last_entity_id")
        if last_id:
            logger.info(f"[CONTEXT] Injecting implicit entity: {last_id}")
            return f" [CONTEXTO IMPLICITO: Se habla de la entidad con ID '{last_id}'. Usa este ID si la pregunta es ambigua.]"
        return ""

    def _update_entity_context(self, conversation_id: str, response: Any):
        """Update context if a single entity was selected."""
        try:
            # Check if lookup operation resulted in single row
            if response.operation == "lookup" and response.row_count == 1:
                # Find the primary ID filter
                entity_id = None
                
                # Method 1: Check filters_applied
                if response.filters_applied:
                    # heuristic parse "COL = 'VAL'"
                    import re
                    match = re.search(r"= '([^']*)'", response.filters_applied[0])
                    if match:
                        entity_id = match.group(1)
                    else:
                        # Try to find number
                        match_num = re.search(r"= (\d+)", response.filters_applied[0])
                        if match_num:
                            entity_id = match_num.group(1)
                
                # Method 2: Check sample_rows for common ID columns if no filter explicit
                if not entity_id and response.sample_rows:
                    row = response.sample_rows[0]
                    # Common ID column names
                    id_cols = ["ID", "ID_EMPLEADO", "NUMERO_EMPLEADO", "CLAVE", "RFC"]
                    for col in id_cols:
                        for k in row.keys():
                            if col in k.upper():
                                entity_id = row[k]
                                break
                        if entity_id: break

                if entity_id:
                    ctx = _chat_contexts.get(str(conversation_id), {})
                    if ctx.get("last_entity_id") != str(entity_id):
                        ctx["last_entity_id"] = str(entity_id)
                        ctx["last_entity_at"] = datetime.now().isoformat()
                        _chat_contexts[str(conversation_id)] = ctx
                        _save_chat_contexts()
                        logger.info(f"[CONTEXT] Updated last_entity_id={entity_id}")
        except Exception as e:
            logger.warning(f"Failed to update entity context: {e}")

    async def _handle_data_query(self, query: str, target_file_id: str, user: User, conversation_id: str = None) -> Tuple[str, List[Source], Dict[str, Any]]:
        """
        Delegate to DataEngine for complete data query pipeline.
        
        CRITICAL: Always use canonical file for tabular queries.
        """
        from verity.modules.data.normalizer import get_file_normalizer
        
        # 1. Resolve Document from ID
        try:
            doc = await self.doc_service.get_document(UUID(target_file_id), user)
            logger.info(f"[DATA_QUERY] file_id={target_file_id}, display_name={doc.display_name}")
        except Exception as e:
            logger.error(f"[DATA_QUERY] Failed to resolve file_id={target_file_id}: {e}")
            return f"Error localizando el archivo: {e}", [], {}

        # 2. Find Canonical File (PREFERRED) or fallback to raw
        normalizer = get_file_normalizer()
        canonical_path = normalizer.get_canonical_path(str(doc.id))
        
        if canonical_path and canonical_path.exists():
            file_path = str(canonical_path.relative_to(Path("uploads")))
            logger.info(f"[DATA_QUERY] CANONICAL_PATH={canonical_path}")
        else:
            # Fallback to legacy path (uploads/{id}_{name})
            search_pattern = f"{doc.id}_*"
            files = list(Path("uploads").glob(search_pattern))
            if not files:
                logger.error(f"[DATA_QUERY] No file found for pattern {search_pattern}")
                return f"No encontré el archivo físico para ID {target_file_id}", [], {}
            
            file_path = files[0].name
            logger.warning(f"[DATA_QUERY] No canonical, using RAW_PATH={files[0]}")

        # 3. Execute through DataEngine
        user_prompt = query
        logger.info(f"[DATA_QUERY] Executing: query='{query[:50]}...', dataset_id={doc.id}, file_path={file_path}")
        
        if conversation_id:
            ctx_str = self._get_entity_context(conversation_id)
            if ctx_str:
                query += ctx_str

        # Preserve the user's original text (before any internal instructions)
        original_user_query = user_prompt

        # Forecast detection (deterministic, no LLM training)
        forecast_triggers = [
            "forecast", "pronost", "predic", "proyecci", "proyección", "proyeccion",
        ]
        should_forecast = any(k in user_prompt.lower() for k in forecast_triggers)

        # Chart detection (Enhanced)
        # Includes short imperative variants like "grafícalo" / "graficarlo".
        chart_triggers = [
            "grafica",
            "gráfica",
            "grafic",
            "graficalo",
            "graficarlo",
            "grafícalo",
            "graficar",
            "chart",
            "plot",
            "visuali",
            "dibuja",
            "pintar",
            "haz una grafica",
            "haz una gráfica",
            "muestralo en grafica",
            "muéstralo en gráfica",
        ]
        should_chart = any(k in user_prompt.lower() for k in chart_triggers)

        # Forecast settings (confidence + optional store filter)
        forecast_confidence = self._infer_forecast_confidence(user_prompt)
        store_val = self._infer_store_filter(user_prompt)

        if should_forecast and forecast_confidence is None and conversation_id:
            conv = _conversations.get(str(conversation_id))
            stored = None
            if conv and isinstance(conv.get("forecast_settings"), dict):
                stored = conv["forecast_settings"].get("confidence")
            if stored is None:
                if conv is not None:
                    conv["pending_forecast_confidence_choice"] = {
                        "original_query": user_prompt,
                        "target_file_id": target_file_id,
                    }
                    _save_conversations()
                return (
                    "Antes de pronosticar: ¿quieres el intervalo por default en **80%** (más apretado) o **95%** (más conservador)?",
                    [],
                    {},
                )
            forecast_confidence = stored

        if should_forecast and forecast_confidence is None:
            forecast_confidence = 0.80

        # Forecast always returns a chart + table, so avoid the chart-choice flow.
        if should_forecast:
            should_chart = False
        
        # SHORTCUT: Chart from Last Result
        shortcut_response = None
        if should_chart and conversation_id and len(original_user_query.split()) < 10:
            try:
                # Get last message with table data from in-memory conversations
                conv = _conversations.get(str(conversation_id))
                if conv and conv.get("messages"):
                    for msg in reversed(conv["messages"]):
                        # msg is a dict, check for table_preview
                        tp = _coerce_table_preview_dict(msg.get("table_preview"))
                        if msg.get("role") == "assistant" and tp and "rows" in tp:
                            logger.info("[DATA_QUERY] SHORTCUT ACTIVATED: Asking user to choose chart type for LAST TABLE.")

                            table_data = tp
                            evidence_ref = msg.get("evidence_ref", "Contexto histórico")

                            # Render a small markdown preview of the prior table
                            import pandas as pd
                            df_prev = pd.DataFrame(table_data["rows"], columns=table_data["columns"])
                            try:
                                table_md = df_prev.head(10).to_markdown(index=False)
                            except ImportError:
                                table_md = df_prev.head(10).to_string(index=False)

                            # Persist pending choice on the conversation (in-memory)
                            conv["pending_chart_choice"] = {
                                "table_preview": table_data,
                                "evidence_ref": evidence_ref,
                                "sources": msg.get("sources") or [],
                                "original_query": query,
                            }

                            x_field, y_field = self._infer_xy_fields(table_data)
                            series_field = self._infer_series_field(table_data, x_field, y_field)
                            recommendation = self._recommend_chart_type(table_data, x_field, y_field, series_field)

                            ask = (
                                "Se encontró la **última tabla** en el historial.\n\n"
                                f"{table_md}\n\n"
                                "¿Qué tipo de gráfica prefieres?\n"
                                "1) Bar\n"
                                "2) Line\n"
                                "3) Scatter\n"
                                "4) Heatmap\n"
                                "5) Treemap\n\n"
                                "6) Stacked Bar\n\n"
                                f"Recomendación: **{recommendation}**. Responde con 1-6."
                            )

                            tp_obj = TablePreview(**table_data)
                            shortcut_response = DataEngineResponse(
                                answer=ask,
                                dataset_id=str(doc.id),
                                answer_type="chart_choice",
                                table_preview=tp_obj,
                                table_markdown=table_md,
                                chart_spec=None,
                                evidence_ref=evidence_ref,
                            )
                            logger.info("[DATA_QUERY] SHORTCUT SUCCESS: pending_chart_choice set")
                            break
            except Exception as e:
                logger.warning(f"[DATA_QUERY] Shortcut failed, falling back to engine: {e}")

        if shortcut_response:
            response = shortcut_response
        else:
            # For forecast, ask DataEngine to return a clean aggregated time series.
            if should_forecast:
                freq = self._infer_forecast_freq(original_user_query)
                horizon = self._infer_forecast_horizon(original_user_query)
                store_instr = ""
                if store_val:
                    store_instr = (
                        f" Si existe una columna de tienda (store/store_id/tienda/sucursal), filtra por '{store_val}'."
                    )
                query = (
                    query
                    + f"\n\n[INSTRUCCIÓN FORECAST]: Genera una tabla agregada para pronóstico con frecuencia '{freq}' "
                    + f"y horizonte {horizon}. Devuelve un DataFrame con EXACTAMENTE 2 columnas llamadas 'time' y 'y'. "
                    + "'time' debe ser fecha/periodo; 'y' debe ser numérico. Ordena asc por 'time'."
                    + " Si detectas dimensión tienda/store y el usuario NO especificó Store=..., puedes incluir UNA columna extra llamada 'store' para que el sistema elija una por defecto."
                    + store_instr
                )

            if should_chart:
                # If query is referential/short and NO shortcut found, guide the agent to use underlying data
                if len(query.split()) < 7:
                    query += ". Genera la tabla de datos necesaria para esta gráfica, basada en el contexto reciente."

            try:
                response = await self.data_engine.query(
                    user_query=query,
                    dataset_id=str(doc.id),
                    file_path=file_path,
                    user_role="admin" if user and user.is_admin else "user",
                    # We ask user to choose chart type (Pie/Bar/Funnel) after table exists.
                    # So we do NOT auto-generate a chart here.
                    generate_chart=False
                )
                
                # Update context for next turn
                if conversation_id:
                    self._update_entity_context(conversation_id, response)
                
                # Log execution details
                logger.info(
                    f"[DATA_QUERY] Result: answer_type={response.answer_type}, "
                    f"code_executed={bool(response.executed_code)}"
                )
                
            except Exception as e:
                logger.error(f"[DATA_QUERY] DataEngine error: {e}")
                return f"Error en el motor de datos: {e}", [], {}

        # Forecast branch (deterministic): build forecast_table + chart_spec
        if should_forecast and response and response.table_preview:
            try:
                import pandas as pd
                from verity.modules.forecast.agent import ForecastAgent

                freq = self._infer_forecast_freq(original_user_query)
                horizon = self._infer_forecast_horizon(original_user_query)

                tp_dict = response.table_preview.model_dump() if hasattr(response.table_preview, "model_dump") else response.table_preview
                cols = list(tp_dict.get("columns") or [])
                rows = list(tp_dict.get("rows") or [])
                df_src = pd.DataFrame(rows, columns=cols)

                # Optional store support: if present, select explicitly or pick most common store.
                used_store = None
                if "store" in df_src.columns:
                    if store_val:
                        used_store = store_val
                    else:
                        try:
                            vc = df_src["store"].astype(str).value_counts(dropna=True)
                            used_store = str(vc.index[0]) if len(vc) else None
                        except Exception:
                            used_store = None

                    if used_store is not None:
                        df_src = df_src[df_src["store"].astype(str) == str(used_store)].copy()
                        # Ensure single series by time
                        if "time" in df_src.columns and "y" in df_src.columns:
                            df_src = df_src[["time", "y"]].groupby("time", as_index=False).sum(numeric_only=True)

                # Enforce required columns (fallback to user question if DataEngine didn't comply)
                if "time" not in df_src.columns or "y" not in df_src.columns:
                    return (
                        "¿Qué columna es la fecha y cuál es la métrica a predecir?",
                        [],
                        {},
                    )

                forecaster = ForecastAgent()
                result = forecaster.forecast(
                    df_src,
                    time_col="time",
                    y_col="y",
                    freq=freq,
                    horizon=horizon,
                    confidence=float(forecast_confidence or 0.80),
                    model_type="auto",
                )

                out = result.forecast_table.copy()
                # Make JSON-safe strings for time
                out["time"] = out["time"].dt.strftime("%Y-%m-%d")

                # UX rule: the confidence interval applies only to the forecast (future rows).
                # For historical rows (where y is present), do NOT populate y_lo/y_hi.
                try:
                    hist_mask = out["y"].notna()
                    out.loc[hist_mask, ["y_lo", "y_hi"]] = None
                except Exception:
                    pass

                # Replace NaN/NaT with None for JSON
                try:
                    import pandas as pd

                    out = out.where(pd.notna(out), None)
                except Exception:
                    pass

                forecast_table = {
                    "columns": ["time", "y", "y_hat", "y_lo", "y_hi"],
                    "rows": out[["time", "y", "y_hat", "y_lo", "y_hi"]].values.tolist(),
                    "total_rows": int(len(out)),
                }

                chart_spec = {
                    "type": "plotly",
                    "spec": {
                        "version": "1.0",
                        "chart_type": "forecast",
                        "title": "Pronóstico",
                        "subtitle": None,
                        "x": {"field": "time", "type": "date", "label": "Fecha"},
                        "y": {"field": "y", "type": "number", "label": "Valor"},
                        "format": self._infer_format("y"),
                    },
                }

                # Overwrite response artifacts for downstream packaging
                response.chart_spec = chart_spec
                response.evidence_ref = (response.evidence_ref or "") + " | " + result.evidence_ref

                # Deterministic assistant message (avoid hallucination)
                assistant_message = (
                    f"Listo: se generó un pronóstico con frecuencia **{freq}** para los próximos **{horizon}** periodos "
                    f"con intervalo **{int(round(float(forecast_confidence or 0.80) * 100))}%**." 
                    + (f" (Store={used_store})." if used_store else "")
                    + " Incluye histórico, pronóstico y una banda de incertidumbre robusta (MAD + winsorización de outliers)."
                )

                # Prepare metadata and return early (skip synthesis LLM + chart-choice)
                from verity.modules.agent.schemas import DataEvidence, ValueInfo

                # Note: For forecasts we typically operate on an aggregated time series.
                # Row-level evidence may be unavailable or not meaningful, so we don't block.

                data_evidence = DataEvidence(
                    operation="forecast",
                    match_policy=response.match_policy or "all",
                    filter_applied=response.filters_applied[0] if response.filters_applied else None,
                    columns_used=response.columns_used or ["time", "y"],
                    row_ids=response.row_ids or [],
                    row_count=response.row_count,
                    row_limit=response.row_limit,
                    sample_rows=response.sample_rows[:3] if response.sample_rows else [],
                    result_value=None,
                )

                source = Source(
                    type="data",
                    file=doc.display_name,
                    canonical_file_id=str(doc.id),
                    data_evidence=data_evidence,
                    id=str(uuid4()),
                    title=f"Forecast: {doc.display_name}",
                    relevance=1.0,
                )

                metadata = {
                    "chart_spec": chart_spec,
                    "table_preview": forecast_table,
                    "evidence_ref": response.evidence_ref,
                }

                return assistant_message, [source], metadata

            except Exception as e:
                logger.error(f"[FORECAST] Failed: {e}")
                return f"No pude generar el pronóstico: {e}", [], {}

        # 4. Validate evidence for tabular results
        # If we got a scalar or table result, the code should exist
        if response.answer_type in ["scalar", "table"] and not response.executed_code:
            logger.warning("[DATA_QUERY] No executed_code for tabular result - suspicious")
        
        # 5. Synthesize human-readable answer using Gemini
        table_context = ""
        logger.info(f"[DEBUG_SYNTHESIS] Answer Type: {type(response.answer)}")
        logger.info(f"[DEBUG_SYNTHESIS] Table Markdown Present: {bool(response.table_markdown)}")
        logger.info(f"[DEBUG_SYNTHESIS] Table Preview Present: {bool(response.table_preview)}")
        
        if response.table_markdown:
            table_context = f"\n\n[DATOS TABULARES DETECTADOS]:\n{response.table_markdown}\n\n(Debes presentar estos datos al usuario si son relevantes. Úsalos para responder.)"
        else:
            logger.warning("[DEBUG_SYNTHESIS] NO TABLE MARKDOWN AVAILABLE!")
        
        # Chart Awareness Instruction
        chart_context = ""
        if response.chart_spec:
            chart_context = """
            [GRÁFICA GENERADA]:
            - El sistema YA ha generado una gráfica interactiva.
            - Se mostrará debajo.
            - TU TAREA: Resume los hallazgos. NO digas "no puedo graficar".
            """

        synthesis_prompt = f"""
        User Question: "{query}"
        
        [RESULTADO DEL SISTEMA]:
        {response.answer}
        
        {table_context}
        {chart_context}
        
        [INSTRUCCIONES]:
        - Responde de forma clara y natural.
        - Si hay [DATOS TABULARES DETECTADOS], inclúyelos en tu respuesta (copia la tabla Markdown o resúmela si es muy larga).
        - Si la respuesta es un número, dilo claramente.
        - NO pidas datos que ya están arriba en [DATOS TABULARES DETECTADOS].
        - PROHIBIDO generar bloques de código Python (matplotlib, pandas) o decir "aquí tienes el código".
        - Si hay [GRÁFICA GENERADA], solo descríbela, NO intentes re-generarla con texto.
        - Responde en Español.
        """
        
        synthesis = self.gemini_client.models.generate_content(
            model=self.model,
            contents=synthesis_prompt
        )

        # If this was a chart request, ask the user which chart type to render next.
        # Store pending state so a follow-up message "1/2/3" can generate the chart without recomputing.
        if should_chart and conversation_id and response.table_preview:
            # Always define a safe default so we never crash the chat pipeline.
            recommendation = "bar"
            try:
                conv = _conversations.get(str(conversation_id))
                if conv is not None:
                    tp_dict = response.table_preview.model_dump() if hasattr(response.table_preview, "model_dump") else response.table_preview
                    x_field, y_field = self._infer_xy_fields(tp_dict)
                    series_field = self._infer_series_field(tp_dict, x_field, y_field)
                    recommendation = self._recommend_chart_type(tp_dict, x_field, y_field, series_field)
                    conv["pending_chart_choice"] = {
                        "table_preview": tp_dict,
                        "evidence_ref": response.evidence_ref,
                        "sources": [],
                        "original_query": query,
                    }
            except Exception as e:
                logger.warning(f"Failed to set pending_chart_choice: {e}")

            synthesis_text = synthesis.text.strip()
            synthesis_text += (
                "\n\n¿Qué tipo de gráfica prefieres?\n"
                "1) Bar\n"
                "2) Line\n"
                "3) Scatter\n"
                "4) Heatmap\n"
                "5) Treemap\n\n"
                "6) Stacked Bar\n\n"
                f"Recomendación: **{recommendation}**. Responde con 1-6."
            )
            # Replace synthesis object text usage downstream
            synthesis_text_override = synthesis_text
        else:
            synthesis_text_override = synthesis.text
        
        # 6. Create Source with structured evidence (audit-ready, no code exposed)
        from verity.modules.agent.schemas import DataEvidence, ValueInfo
        
        # Build ValueInfo for scalar results
        result_value = None
        if response.value_type and response.raw_value is not None:
            formatted_value = response.answer  # Use the formatted answer
            result_value = ValueInfo(
                value_type=response.value_type,
                raw_value=response.raw_value,
                formatted=formatted_value,
                unit=response.unit
            )
        
        # CRITICAL: Block if no row_ids (unverifiable response)
        # Can be disabled for local MVP via AGENT_ENFORCE_ROW_IDS_GUARD=false.
        from verity.config import get_settings
        settings = get_settings()
        enforce_guard = bool(settings.agent_enforce_row_ids_guard) and settings.is_production

        # If there are zero matching rows, report that explicitly (not an audit failure).
        if enforce_guard and (not response.row_ids) and response.answer_type in ["scalar", "table"]:
            if getattr(response, "row_count", 0) == 0:
                logger.info(
                    f"[DATA_QUERY] EMPTY: row_count=0 for {response.answer_type}. "
                    f"File: {doc.display_name}, Query: {query[:50]}..."
                )
                return (
                    "No encontré filas que coincidan con ese filtro/consulta. "
                    "Prueba especificando un valor que exista (ej: empresa exacta, periodo, o un ID), "
                    "o quita filtros como Sindicalizado/Proyecto para validar.",
                    [],
                    {}
                )

            logger.warning(
                f"[DATA_QUERY] BLOCKED: No row_ids for {response.answer_type} result. "
                f"File: {doc.display_name}, Query: {query[:50]}..."
            )
            return (
                "⚠️ No verificable: La respuesta no incluye evidencia de filas específicas. "
                "Por favor reformula la pregunta de manera más específica.",
                [],
                {}
            )
        
        data_evidence = DataEvidence(
            operation=response.operation or "lookup",
            match_policy=response.match_policy or "all",
            filter_applied=response.filters_applied[0] if response.filters_applied else None,
            columns_used=response.columns_used or [],
            row_ids=response.row_ids or [],
            row_count=response.row_count,
            row_limit=response.row_limit,
            sample_rows=response.sample_rows[:3] if response.sample_rows else [],
            result_value=result_value
        )
        
        source = Source(
            type="data",
            file=doc.display_name,
            canonical_file_id=str(doc.id),
            data_evidence=data_evidence,
            # Legacy fields for backwards compatibility
            id=str(uuid4()),
            title=f"Data Engine: {doc.display_name}",
            relevance=1.0
        )
        
        logger.info(
            f"[DATA_QUERY] Complete: file_id={target_file_id}, "
            f"operation={response.operation}, row_count={response.row_count}, "
            f"row_ids={response.row_ids[:5] if response.row_ids else []}..."
        )
        
        tp_dict = response.table_preview.model_dump() if response.table_preview else None
        if tp_dict is None and response.table_markdown:
            tp_dict = self._table_preview_from_markdown(response.table_markdown)

        metadata = {
            "chart_spec": response.chart_spec,
            "table_preview": tp_dict,
            "evidence_ref": response.evidence_ref,
        }
        
        return synthesis_text_override, [source], metadata

    # ---------------------------------------------------------------------
    # Chart choice helpers
    # ---------------------------------------------------------------------

    def _parse_chart_choice(self, text: str) -> str | None:
        t = (text or "").strip().lower()
        # common variants
        if t in {"1", "bar", "barra", "barras", "bar chart"}:
            return "bar"
        if t in {"2", "line", "línea", "linea", "line chart"}:
            return "line"
        if t in {"3", "scatter", "dispersión", "dispersion", "scatter plot"}:
            return "scatter"
        if t in {"4", "heatmap", "mapa de calor"}:
            return "heatmap"
        if t in {"5", "treemap", "tree map"}:
            return "treemap"
        if t in {"6", "stacked", "stacked bar", "stacked_bar", "apilada", "apiladas", "barra apilada", "barras apiladas"}:
            return "stacked_bar"
        # allow formats like "1." or "2)"
        if re.match(r"^1\D*$", t):
            return "bar"
        if re.match(r"^2\D*$", t):
            return "line"
        if re.match(r"^3\D*$", t):
            return "scatter"
        if re.match(r"^4\D*$", t):
            return "heatmap"
        if re.match(r"^5\D*$", t):
            return "treemap"
        if re.match(r"^6\D*$", t):
            return "stacked_bar"
        return None

    def _infer_series_field(self, table_data: Dict[str, Any], x_field: str | None, y_field: str | None) -> str | None:
        """Pick a likely categorical series/parent field distinct from x/y."""
        columns = list(table_data.get("columns") or [])
        rows = list(table_data.get("rows") or [])
        if not columns or not rows:
            return None

        def numeric_score(col_index: int) -> float:
            ok = 0
            total = 0
            for r in rows[:50]:
                if col_index >= len(r):
                    continue
                v = r[col_index]
                if v is None or v == "":
                    continue
                total += 1
                try:
                    if isinstance(v, (int, float)):
                        ok += 1
                    else:
                        s = str(v)
                        s = re.sub(r"[^0-9.\-]", "", s)
                        float(s)
                        ok += 1
                except Exception:
                    pass
            return (ok / total) if total else 0.0

        candidates: list[tuple[str, float, int]] = []
        for i, c in enumerate(columns):
            if c == x_field or c == y_field:
                continue
            candidates.append((c, numeric_score(i), i))

        # prefer non-numeric columns
        for c, sc, _i in sorted(candidates, key=lambda x: x[1]):
            if sc < 0.7:
                return c
        return None

    def _infer_xy_fields(self, table_data: Dict[str, Any]) -> tuple[str | None, str | None]:
        columns = list(table_data.get("columns") or [])
        rows = list(table_data.get("rows") or [])
        if not columns or not rows:
            return None, None

        def numeric_score(col_index: int) -> float:
            ok = 0
            total = 0
            for r in rows[:50]:
                if col_index >= len(r):
                    continue
                v = r[col_index]
                if v is None or v == "":
                    continue
                total += 1
                try:
                    if isinstance(v, (int, float)):
                        ok += 1
                    else:
                        s = str(v)
                        s = re.sub(r"[^0-9.\-]", "", s)
                        float(s)
                        ok += 1
                except Exception:
                    pass
            return (ok / total) if total else 0.0

        scores = [(c, numeric_score(i), i) for i, c in enumerate(columns)]
        scores.sort(key=lambda x: x[1], reverse=True)
        y_field = scores[0][0] if scores and scores[0][1] >= 0.7 else None

        # pick a non-numeric-ish column for x
        x_field = None
        for c, sc, _i in scores:
            if c == y_field:
                continue
            if sc < 0.7:
                x_field = c
                break
        if x_field is None:
            # fallback to first column that's not y
            for c in columns:
                if c != y_field:
                    x_field = c
                    break
        return x_field, y_field

    def _recommend_chart_type(self, table_data: Dict[str, Any], x_field: str | None, y_field: str | None, series_field: str | None) -> str:
        rows = list(table_data.get("rows") or [])
        n = len(rows)
        if not x_field or not y_field or n == 0:
            return "bar"

        # v1 heuristic:
        # - If we have a second categorical dimension -> heatmap is often best
        # - If x looks temporal -> line
        # - If both x and y are numeric-ish -> scatter
        # - Else -> bar
        if series_field:
            # If we have series, prefer stacked_bar for small cardinalities; otherwise heatmap.
            try:
                col_idx = {c: i for i, c in enumerate(table_data.get("columns") or [])}
                x_idx = col_idx.get(x_field)
                s_idx = col_idx.get(series_field)
                if x_idx is not None and s_idx is not None:
                    x_vals = set()
                    s_vals = set()
                    for r in rows[:300]:
                        if x_idx < len(r):
                            x_vals.add(str(r[x_idx]))
                        if s_idx < len(r):
                            s_vals.add(str(r[s_idx]))
                    if len(x_vals) <= 12 and len(s_vals) <= 6:
                        return "stacked_bar"
            except Exception:
                pass
            if n <= 200:
                return "heatmap"

        x_lower = (x_field or "").lower()
        if any(k in x_lower for k in ["fecha", "date", "mes", "año", "anio", "periodo", "period", "día", "dia"]):
            return "line"

        # Try numeric-ness of x by sampling
        try:
            col_idx = {c: i for i, c in enumerate(table_data.get("columns") or [])}
            x_idx = col_idx.get(x_field)
            y_idx = col_idx.get(y_field)
            if x_idx is not None and y_idx is not None:
                x_num = 0
                y_num = 0
                total = 0
                for r in rows[:30]:
                    if x_idx >= len(r) or y_idx >= len(r):
                        continue
                    total += 1
                    xv = r[x_idx]
                    yv = r[y_idx]
                    try:
                        float(re.sub(r"[^0-9.\-]", "", str(xv)))
                        x_num += 1
                    except Exception:
                        pass
                    try:
                        float(re.sub(r"[^0-9.\-]", "", str(yv)))
                        y_num += 1
                    except Exception:
                        pass
                if total and (x_num / total) >= 0.7 and (y_num / total) >= 0.7:
                    return "scatter"
        except Exception:
            pass

        return "bar"

    def _infer_format(self, y_field: str | None) -> Dict[str, Any] | None:
        if not y_field:
            return None
        y = y_field.lower()
        if any(k in y for k in ["monto", "importe", "total", "pagado", "pago", "precio", "costo", "coste", "mxn", "usd"]):
            return {"type": "currency", "unit": None}
        if any(k in y for k in ["%", "porcentaje", "tasa", "ratio", "pct"]):
            return {"type": "percent", "unit": None}
        return {"type": "number", "unit": None}

    def _build_chart_from_pending(self, pending: Dict[str, Any], chosen_type: str) -> tuple[Dict[str, Any], Dict[str, Any], str | None]:
        table_preview = pending.get("table_preview") or {}
        evidence_ref = pending.get("evidence_ref")
        original_query = pending.get("original_query") or ""

        x_field, y_field = self._infer_xy_fields(table_preview)
        if not x_field or not y_field:
            raise ValueError("No pude inferir columnas x/y para graficar")

        series_field = self._infer_series_field(table_preview, x_field, y_field)
        if chosen_type in {"heatmap", "treemap", "stacked_bar"} and not series_field:
            if chosen_type == "stacked_bar":
                raise ValueError("falta una columna de serie para apilar (campo 'series')")
            raise ValueError("falta una segunda dimensión categórica (campo 'series')")

        title_base = original_query.strip() or "Gráfica"
        title = title_base[:80]

        spec: Dict[str, Any] = {
            "version": "1.0",
            "chart_type": chosen_type,
            "title": title,
            "subtitle": None,
            "x": {"field": x_field, "type": "category", "label": x_field},
            "y": {"field": y_field, "type": "number", "label": y_field},
            "series": (
                {"field": series_field, "type": "category", "label": series_field}
                if series_field and chosen_type in {"bar", "line", "scatter", "stacked_bar", "heatmap", "treemap"}
                else None
            ),
            "format": self._infer_format(y_field),
        }

        wrapper = {"type": "plotly", "spec": spec}
        return wrapper, table_preview, evidence_ref
        
    # Helpers
    def _create_conversation(self, conversation_id: UUID, user: User) -> dict:
        now = datetime.now(timezone.utc)
        conversation = {
            "id": str(conversation_id),
            "user_id": str(user.id),
            "org_id": str(user.org_id),
            "title": None,
            "messages": [],
            "message_count": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        _conversations[str(conversation_id)] = conversation
        _save_conversations()
        return conversation

    def _clean_response(self, response: str) -> str:
        return response.strip()

    def _table_preview_from_markdown(self, table_markdown: str) -> dict[str, Any] | None:
        md = (table_markdown or "").strip()
        if not md:
            return None

        lines = [ln.strip() for ln in md.splitlines() if ln.strip()]
        if len(lines) < 2:
            return None

        header_idx: int | None = None
        for i, ln in enumerate(lines[:10]):
            if ln.startswith("|") and "|" in ln[1:]:
                header_idx = i
                break
        if header_idx is None or header_idx + 1 >= len(lines):
            return None

        def split_row(row: str) -> list[str]:
            return [p.strip() for p in row.strip().strip("|").split("|")]

        columns = split_row(lines[header_idx])
        if not columns or all(not c for c in columns):
            return None

        sep = lines[header_idx + 1]
        is_sep = (
            sep.startswith("|")
            and all(set(p.replace(":", "").strip()) <= {"-"} for p in split_row(sep) if p)
        )

        start = header_idx + 2 if is_sep else header_idx + 1
        rows: list[list[Any]] = []
        for ln in lines[start:]:
            if not ln.startswith("|"):
                break
            values = split_row(ln)
            if len(values) != len(columns):
                continue
            rows.append(values)
            if len(rows) >= 200:
                break

        if not rows:
            return None

        return {"columns": columns, "rows": rows, "total_rows": len(rows)}

    # ---------------------------------------------------------------------
    # Forecast helpers (deterministic)
    # ---------------------------------------------------------------------

    def _infer_forecast_freq(self, text: str) -> str:
        """Infer pandas frequency code from prompt (default: M)."""
        t = (text or "").lower()
        if "diari" in t or "cada dia" in t or "cada día" in t:
            return "D"
        if "seman" in t:
            return "W"
        if "mens" in t or "mes" in t or "meses" in t:
            return "M"
        if "trimes" in t or "quarter" in t:
            return "Q"
        if "anual" in t or "año" in t or "anio" in t:
            return "Y"
        return "M"

    def _infer_forecast_horizon(self, text: str) -> int:
        """Infer horizon (period count) from prompt (default: 6)."""
        t = (text or "").lower()
        # Common patterns: "próximos 6 meses", "a 12 semanas"
        m = re.search(r"(proximos|próximos|siguientes|a)\s+(\d{1,3})\s+(dias|días|semanas|meses|años|anos)", t)
        if m:
            n = int(m.group(2))
            unit = m.group(3)
            # Convert to period counts based on inferred freq
            if "sem" in unit:
                return n
            if "mes" in unit:
                return n
            if "dia" in unit or "día" in unit:
                return n
            if "año" in unit or "ano" in unit:
                return n
        m2 = re.search(r"\b(\d{1,3})\b", t)
        if m2 and any(k in t for k in ["horizonte", "periodos", "períodos", "semanas", "meses", "dias", "días"]):
            return int(m2.group(1))
        return 6

    def _infer_forecast_confidence(self, text: str) -> float | None:
        """Infer confidence from prompt, e.g. '95%' or '80%'. Returns 0.95/0.80 or None."""
        t = (text or "").lower()
        m = re.search(r"\b(\d{2})\s*%\b", t)
        if not m:
            return None
        pct = int(m.group(1))
        if pct < 50 or pct > 99:
            return None

        # Snap to common values
        if pct >= 93:
            return 0.95
        if pct <= 85:
            return 0.80
        return 0.95

    def _parse_forecast_confidence_choice(self, text: str) -> float | None:
        """Parse a user reply choosing default interval: '80', '80%', '95', '95%'."""
        t = (text or "").strip().lower()
        m = re.search(r"\b(80|95)\b", t)
        if not m:
            return None
        return 0.80 if m.group(1) == "80" else 0.95

    def _infer_store_filter(self, text: str) -> str | None:
        """Infer store selector from prompt, e.g. 'store=1', 'tienda 3'."""
        t = text or ""
        m = re.search(r"\b(store|tienda|sucursal)\s*(=|:)?\s*([\w-]+)\b", t, re.IGNORECASE)
        if not m:
            return None
        return m.group(3)

    # Legacy methods for Router compatibility (listing/deleting conversations)
    # Copied from original service to maintain API contract
    async def list_conversations(self, user: User, page_size: int = 20, page_token: str | None = None) -> tuple[list[ConversationSummary], str | None, int]:
        user_convs = [c for c in _conversations.values() if c.get("user_id") == str(user.id) and c.get("org_id") == str(user.org_id)]
        user_convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        offset = int(page_token) if page_token else 0
        items = user_convs[offset : offset + page_size]
        next_token = str(offset + page_size) if offset + len(items) < len(user_convs) else None
        summaries = [ConversationSummary(id=UUID(c["id"]), title=c.get("title"), message_count=c.get("message_count", 0), created_at=c.get("created_at"), updated_at=c.get("updated_at")) for c in items]
        return summaries, next_token, len(user_convs)

    async def get_conversation(self, conversation_id: UUID, user: User) -> ConversationResponse:
        conv_id_str = str(conversation_id)
        if conv_id_str not in _conversations: raise NotFoundException("conversation", conversation_id)
        conversation = _conversations[conv_id_str]
        messages = [
            ConversationMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                timestamp=m.get("timestamp"),
                request_id=UUID(m["request_id"]) if m.get("request_id") else None,
                sources=m.get("sources"),
                chart_spec=m.get("chart_spec"),
                table_preview=m.get("table_preview"),
                evidence_ref=m.get("evidence_ref"),
            )
            for m in conversation.get("messages", [])
        ]
        return ConversationResponse(id=UUID(conversation["id"]), title=conversation.get("title"), messages=messages, created_at=conversation.get("created_at"), updated_at=conversation.get("updated_at"))

    async def delete_conversation(self, conversation_id: UUID, user: User) -> bool:
        conv_id_str = str(conversation_id)
        if conv_id_str in _conversations:
            del _conversations[conv_id_str]
            _save_conversations()
        return True
