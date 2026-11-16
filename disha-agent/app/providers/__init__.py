"""Provider abstraction — one interface, three implementations.

  * GeminiProvider — Google Gemini REST API (primary when key present)
  * GroqProvider   — Groq OpenAI-compatible endpoint (fallback when key present)
  * DemoProvider   — deterministic planner; used ONLY when no real provider is
                     configured (demo mode). It is explicitly labeled, never
                     disguises a provider failure.

Failover policy (service layer): try primary with one short retry → fallback
→ if both are configured and both fail, raise 503. Demo provider is never a
substitute for a failed real provider.
"""
from __future__ import annotations

from ..config import settings
from .base import BaseProvider, ProviderError
from .demo import DemoProvider
from .gemini import GeminiProvider
from .groq import GroqProvider

__all__ = ["BaseProvider", "ProviderError", "get_provider", "get_fallback_provider"]


def get_provider() -> BaseProvider:
    """Return the primary provider (or demo provider when nothing configured)."""
    if settings.demo_mode:
        return DemoProvider()
    if settings.gemini_api_key:
        return GeminiProvider()
    if settings.groq_api_key:
        return GroqProvider()
    return DemoProvider()


def get_fallback_provider() -> BaseProvider | None:
    if settings.demo_mode:
        return None
    primary = get_provider()
    if isinstance(primary, GeminiProvider) and settings.groq_api_key:
        return GroqProvider()
    if isinstance(primary, GroqProvider) and settings.gemini_api_key:
        return GeminiProvider()
    return None
