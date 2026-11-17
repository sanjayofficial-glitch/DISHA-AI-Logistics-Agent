"""Groq provider via its OpenAI-compatible endpoint."""
from __future__ import annotations

import httpx

from ..config import settings
from .base import BaseProvider, ProviderError


class GroqProvider(BaseProvider):
    name = "groq"

    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise ProviderError("Groq API key not configured")
        self._key = settings.groq_api_key
        self._model = settings.groq_model

    def complete(self, system: str, user: str) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": 1024,
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {self._key}"}
        try:
            resp = httpx.post(url, headers=headers, json=payload,
                               timeout=settings.provider_timeout_s)
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"groq transport error: {exc.__class__.__name__}", retryable=True
            ) from exc
        if resp.status_code != 200:
            retryable = resp.status_code == 429 or resp.status_code >= 500
            raise ProviderError(f"groq HTTP {resp.status_code}", retryable=retryable)
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("groq returned empty response") from None
        return text.strip()
