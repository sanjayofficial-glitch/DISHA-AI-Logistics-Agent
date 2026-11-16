"""DISHA configuration — pydantic-settings, env-driven.

All secrets live in environment variables (or a local .env file). Nothing
here is a real credential; values are dev placeholders.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Service identity -------------------------------------------------
    app_name: str = "DISHA"
    version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"

    # --- LLM providers (keys optional; demo mode when both absent) --------
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    # --- Supabase (optional; SQLite demo store when absent) ---------------
    supabase_url: str | None = None
    supabase_anon_key: str | None = None

    # --- Auth — Clerk->Supabase JWT contract ------------------------------
    # SUPABASE_JWT_SECRET signs the HS256 JWTs. In demo mode (development +
    # no secret configured) a fixed local dev secret is used so the flow can
    # be exercised end-to-end without external services. NEVER ship a real
    # secret here.
    supabase_jwt_secret: str | None = None
    clerk_expected_issuer: str | None = None
    clerk_expected_audience: str | None = None

    # --- CORS -------------------------------------------------------------
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ]

    # --- Storage ----------------------------------------------------------
    data_dir: Path = Path("data")
    db_path: Path = Path("data/disha.db")

    # --- Limits -----------------------------------------------------------
    chat_rate_limit_per_min: int = 30
    write_rate_limit_per_min: int = 10
    max_message_chars: int = 4000
    max_payload_chars: int = 4000
    memory_retrieval_cap: int = 20
    history_retrieval_cap: int = 20
    search_limit: int = 20

    # Provider timeout / retry
    provider_timeout_s: float = 20.0
    provider_retries: int = 1

    @property
    def demo_mode(self) -> bool:
        """True when no real LLM provider is configured.

        Demo mode uses the deterministic planner (clearly labeled). When a
        real key IS configured, provider failures surface as honest 503s —
        never a fake reply.
        """
        return not (self.gemini_api_key or self.groq_api_key)

    @property
    def jwt_secret(self) -> str:
        if self.supabase_jwt_secret:
            return self.supabase_jwt_secret
        # Dev-only fallback (never used in production). 40+ bytes for HS256.
        return "disha-dev-only-secret-not-for-production-0123456789abcdef"

    @property
    def demo_login_enabled(self) -> bool:
        """POST /auth/demo-login is only reachable when no real Supabase JWT
        secret has been configured (i.e. demo mode)."""
        return self.supabase_jwt_secret is None


settings = Settings()
