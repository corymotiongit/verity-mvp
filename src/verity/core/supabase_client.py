"""
Verity Core - Supabase Client.

Provides configured Supabase client for database operations.
"""

from functools import lru_cache

from supabase import Client, create_client

from verity.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """
    Get configured Supabase client.

    Uses service role key for server-side operations.
    Cached to reuse the same client instance.
    """
    settings = get_settings()
    return create_client(
        supabase_url=settings.supabase.url,
        supabase_key=settings.supabase.service_role_key,
    )
