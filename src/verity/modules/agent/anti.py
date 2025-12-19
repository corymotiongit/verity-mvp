"""ANTI (Guard / Output Normalizer).

Deterministic post-processor that validates/verifies assistant output using
structured tool results and chat context.

Goals:
- No hallucinations: if evidence is missing -> "No verificable".
- No code exposure: strip code blocks.
- Always include FUENTES block for sourced answers.

This module intentionally avoids LLM calls.
"""

from __future__ import annotations

import re
from typing import Any

from verity.modules.agent.schemas import Source


def _strip_code_blocks(text: str) -> str:
    # Remove fenced blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove obvious inline code-y lines
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith(("import ", "from "))]
    return "\n".join(lines).strip()


def format_fuentes(sources: list[Source]) -> str:
    if not sources:
        return "FUENTES: (sin fuentes)"

    parts: list[str] = ["FUENTES:"]
    for s in sources:
        st = getattr(s, "type", None)

        if st == "data" and s.data_evidence is not None:
            ev = s.data_evidence
            row_ids = list(ev.row_ids or [])
            row_ids_str = "[]"
            if row_ids:
                preview = row_ids[:20]
                row_ids_str = str(preview) + (" …" if len(row_ids) > 20 else "")

            row_count_val = getattr(ev, "row_count", None)
            row_count_str = str(row_count_val) if isinstance(row_count_val, int) else "?"

            cols_used = ev.columns_used or []
            cols_str = ",".join(cols_used[:10]) + ("…" if len(cols_used) > 10 else "")

            parts.append(
                "- type=data"
                + (f" file={s.file}" if s.file else "")
                + (f" row_ids={row_ids_str}")
                + (f" filter={ev.filter_applied}" if ev.filter_applied else "")
                + (f" columns={cols_str}" if cols_str else "")
                + (f" row_count={row_count_str}")
            )
            continue

        if st == "doc" and s.doc_evidence is not None:
            ev = s.doc_evidence
            parts.append(
                "- type=doc"
                + (f" file={s.file}" if s.file else "")
                + (f" page={ev.page}" if ev.page is not None else "")
                + (f" section={ev.section}" if ev.section else "")
            )
            continue

        # web or legacy
        parts.append(
            "- type=" + (st or "unknown") + (f" file={s.file}" if s.file else "")
        )

    return "\n".join(parts)


def anti_normalize(
    *,
    user_message: str,
    chat_context: dict[str, Any] | None,
    assistant_message: str,
    sources: list[Source],
    data_meta: dict[str, Any] | None,
) -> tuple[str, dict[str, Any] | None]:
    """Apply ANTI rules to final output."""
    _ = user_message
    chat_context = chat_context or {}

    # Effective guard: only enforce in production (MVP convenience)
    try:
        from verity.config import get_settings

        settings = get_settings()
        enforce_guard = bool(settings.agent_enforce_row_ids_guard) and bool(settings.is_production)
    except Exception:
        enforce_guard = False

    # NOTE: PII redaction intentionally disabled. Admin users require full access.

    data_sources = [s for s in sources if getattr(s, "type", None) == "data" and s.data_evidence is not None]
    fuentes = format_fuentes(sources)
    if not data_sources:
        # Non-data sourced responses: still strip code blocks, but include FUENTES.
        cleaned = _strip_code_blocks(assistant_message)
        if "FUENTES:" not in cleaned:
            cleaned = f"{cleaned}\n\n{fuentes}" if cleaned else fuentes
        return cleaned, data_meta

    # Row evidence policy
    missing_row_ids = [s for s in data_sources if not (s.data_evidence.row_ids or [])]

    if missing_row_ids:
        # If query returned zero rows, this is not an audit failure: report "no matches".
        # (Common when the user asks follow-ups like "grafícalo" and the system re-runs a query.)
        if all((getattr(s.data_evidence, "row_count", 0) or 0) == 0 for s in missing_row_ids):
            msg = (
                "No encontré filas que coincidan con tu consulta. "
                "Prueba con un filtro/ID/periodo distinto o confirma qué subset quieres graficar."
            )
            return f"{msg}\n\n{fuentes}", data_meta

        # Otherwise, enforce only when guard is effectively enabled.
        if enforce_guard:
            msg = (
                "No verificable: falta evidencia de filas (row_ids) para responder con auditoría. "
                "Hace falta un filtro/ID/periodo más específico o una consulta que devuelva filas trazables."
            )
            return f"{msg}\n\n{fuentes}", data_meta

    cleaned = _strip_code_blocks(assistant_message)

    # Avoid first-person phrasing for dataset outputs when possible (light-touch).
    cleaned = re.sub(r"\b(yo|mi|m[íi]o|m[íi]a|conmigo|me)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\blo\s+siento\b", "Ocurrió un error", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bgener[ée]\b", "se generó", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bencontr[ée]\b", "se encontró", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpuedo\b", "se puede", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpodr[íi]a\b", "se podría", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if "FUENTES:" not in cleaned:
        cleaned = f"{cleaned}\n\n{fuentes}" if cleaned else fuentes

    return cleaned, data_meta
