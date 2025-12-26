"""Semantics context store (v1.1).

Goal:
- Lightweight, in-process conversational context for v2 queries.
- Store last resolved metric/table and pending disambiguation options.

Constraints:
- Additive only. No changes to the immutable pipeline flow.
- Best-effort memory (TTL); safe to lose state.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any


@dataclass
class SemanticsContext:
    last_metric: str | None = None
    last_table: str | None = None
    last_alias: str | None = None

    # One-turn guided disambiguation
    pending_candidates: list[dict[str, Any]] | None = None

    # Timestamp for TTL
    updated_at_epoch_s: float = 0.0


class SemanticsContextStore:
    """In-memory context with TTL.

    This is intentionally tiny and best-effort.
    """

    def __init__(self, ttl_seconds: int = 30 * 60):
        self._ttl_seconds = int(ttl_seconds)
        self._store: dict[str, SemanticsContext] = {}

    def _now(self) -> float:
        return float(time())

    def _is_expired(self, ctx: SemanticsContext) -> bool:
        if not ctx.updated_at_epoch_s:
            return True
        return (self._now() - ctx.updated_at_epoch_s) > self._ttl_seconds

    def get(self, conversation_id: str) -> SemanticsContext:
        cid = str(conversation_id)
        ctx = self._store.get(cid)
        if ctx is None:
            ctx = SemanticsContext(updated_at_epoch_s=self._now())
            self._store[cid] = ctx
            return ctx

        if self._is_expired(ctx):
            ctx = SemanticsContext(updated_at_epoch_s=self._now())
            self._store[cid] = ctx
            return ctx

        return ctx

    def set_last_resolution(self, *, conversation_id: str, metric: str | None, table: str | None, alias: str | None) -> None:
        ctx = self.get(conversation_id)
        ctx.last_metric = metric
        ctx.last_table = table
        ctx.last_alias = alias
        ctx.updated_at_epoch_s = self._now()

    def set_pending_candidates(self, *, conversation_id: str, candidates: list[dict[str, Any]]) -> None:
        ctx = self.get(conversation_id)
        ctx.pending_candidates = list(candidates)
        ctx.updated_at_epoch_s = self._now()

    def clear_pending_candidates(self, *, conversation_id: str) -> None:
        ctx = self.get(conversation_id)
        ctx.pending_candidates = None
        ctx.updated_at_epoch_s = self._now()
