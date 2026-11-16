"""Base provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    pass


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return assistant reply text."""
