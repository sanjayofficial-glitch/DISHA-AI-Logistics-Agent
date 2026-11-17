"""Base provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    """Provider failure. `retryable=True` means a retry may help (rate limit
    (429), 5xx, transport/network failure). Permanent errors (4xx auth/invalid
    request, bad response payload) are not retryable."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return assistant reply text."""
