"""Verity Core - Users repository (Supabase).

Rule of thumb:
- Redis = temporal auth state (OTP + attempts)
- Supabase = identity (wa_id, phone_number, last_login)

This module persists identity only. It never stores OTP.
"""

from __future__ import annotations

from datetime import datetime

from verity.core.supabase_client import get_supabase_client


def upsert_user_identity(*, wa_id: str, phone_number: str | None, last_login: datetime) -> None:
    """Upsert a user row by wa_id.

    Schema expectation (Supabase):
    - users(id uuid primary key, wa_id text unique, phone_number text, created_at, last_login)

    We write:
    - wa_id (required)
    - phone_number (optional)
    - last_login (required)

    The database should set created_at on insert.
    """

    wa_id = (wa_id or "").strip()
    if not wa_id:
        raise ValueError("wa_id is required")

    client = get_supabase_client()

    payload: dict[str, object] = {
        "wa_id": wa_id,
        "last_login": last_login.isoformat(),
    }
    if phone_number is not None:
        payload["phone_number"] = phone_number

    # supabase-py: table().upsert(..., on_conflict=...).execute()
    client.table("users").upsert(payload, on_conflict="wa_id").execute()
