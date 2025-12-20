"""
Verity Configuration Module.

Handles all application settings, feature flags, and environment configuration.
Uses pydantic-settings for validation and type safety.

Architecture: Gemini Developer API (API key) - NO Vertex AI.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlags(BaseSettings):
    """Feature flags for enabling/disabling modules."""

    model_config = SettingsConfigDict(env_prefix="FEATURE_")

    documents: bool = True
    approvals: bool = True
    agent: bool = True
    reports: bool = True
    charts: bool = True
    forecast: bool = True
    logs: bool = True
    audit: bool = True

    def to_dict(self) -> dict[str, bool]:
        """Return feature flags as dictionary for health endpoint."""
        return {
            "documents": self.documents,
            "approvals": self.approvals,
            "agent": self.agent,
            "reports": self.reports,
            "charts": self.charts,
            "forecast": self.forecast,
            "logs": self.logs,
            "audit": self.audit,
        }


class SupabaseSettings(BaseSettings):
    """Supabase configuration for authentication."""

    model_config = SettingsConfigDict(env_prefix="SUPABASE_")

    url: str = Field(default="https://demo.supabase.co", description="Supabase project URL")
    anon_key: str = Field(default="demo-anon-key", description="Supabase anonymous key")
    service_role_key: str = Field(default="demo-service-role-key", description="Supabase service role key")
    jwt_secret: str = Field(default="demo-jwt-secret-for-development-only", description="JWT secret for token validation")


class GCPSettings(BaseSettings):
    """Google Cloud Platform configuration (for Secret Manager only)."""

    model_config = SettingsConfigDict(env_prefix="GCP_")

    project_id: str = Field(default="verity-mvp", description="GCP Project ID")
    # Note: No Vertex AI settings - using Gemini Developer API


class GeminiSettings(BaseSettings):
    """Gemini API configuration."""

    model_config = SettingsConfigDict(env_prefix="GEMINI_")

    api_key: str = Field(default="", description="Gemini API Key")


class N8NSettings(BaseSettings):
    """n8n webhook configuration (OTP)."""

    model_config = SettingsConfigDict(env_prefix="N8N_")

    base_url: str = Field(default="https://shadowcat.cloud", description="Base URL for n8n (e.g. https://n8n.example.com)")
    otp_request_path: str = Field(
        default="/webhook/shadowcat-otp-request",
        description="Webhook path for OTP request",
    )
    otp_validate_path: str = Field(
        default="/webhook/shadowcat-otp-validate",
        description="Webhook path for OTP validate",
    )
    timeout_seconds: float = Field(default=8.0, description="HTTP timeout when calling n8n")


class RedisSettings(BaseSettings):
    """Redis configuration (session validation)."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    session_key_prefix: str = Field(
        default="session:",
        description="Redis key prefix for session tokens (key = prefix + <token>)",
    )
    otp_key_prefix: str = Field(
        default="otp:",
        description="Redis key prefix for OTP entries (key = prefix + <userId>)",
    )

    # MVP defaults (until org membership is stored per-session)
    default_org_id: str = Field(
        default="00000000-0000-0000-0000-000000000100",
        description="Default org_id used when session does not include org context",
    )
    default_org_name: str = Field(default="Test Organization")
    default_org_slug: str = Field(default="test-org")
    default_file_search_store_id: str | None = Field(
        default="fileSearchStores/veritytest-organization0000-358ive08qbin",
        description="Default File Search store ID for MVP",
    )


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_log_level: str = "INFO"

    # Auth (MVP / local convenience)
    auth_insecure_dev_bypass: bool = Field(
        default=False,
        description="If true (and not production), bypass Redis session validation and allow requests with any (or missing) Bearer token. Intended for local MVP only.",
        validation_alias="AUTH_INSECURE_DEV_BYPASS",
    )

    # Agent / Audit (MVP convenience)
    agent_enforce_row_ids_guard: bool = Field(
        default=True,
        description="If true, block tabular answers that lack row_ids evidence (audit guard).",
        validation_alias="AGENT_ENFORCE_ROW_IDS_GUARD",
    )

    # Nested settings
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    supabase: SupabaseSettings = Field(default_factory=SupabaseSettings)
    gcp: GCPSettings = Field(default_factory=GCPSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)

    n8n: N8NSettings = Field(default_factory=N8NSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
