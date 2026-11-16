"""Google Gemini provider via REST (no heavy SDK dependency)."""
from __future__ import annotations

import httpx

from ..config import settings
from .base import BaseProvider, ProviderError


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise ProviderError("Gemini API key not configured")
        self._key = settings.gemini_api_key
        self._model = settings.gemini_model

    def complete(self, system: str, user: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.3},
        }
        try:
            resp = httpx.post(
                url,
                params={"key": self._key},
                json=payload,
                timeout=settings.provider_timeout_s,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"gemini transport error: {exc.__class__.__name__}") from exc
        if resp.status_code != 200:
            raise ProviderError(f"gemini HTTP {resp.status_code}")
        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("gemini returned empty response") from None
        return text.strip()
