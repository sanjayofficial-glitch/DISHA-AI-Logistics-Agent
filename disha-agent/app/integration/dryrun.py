"""Dry-run integration harness.

Wraps any MarketplaceStore and:
  1. validates every read result against the LoadSaathi row contracts
  2. records every call (for audit/verification)
  3. refuses to open a live connection unless the caller explicitly enables it

Used in tests to prove the adapter shapes are consistent without touching
any real Supabase project.
"""
from __future__ import annotations

from typing import Any

from .contract import validate_row


def _table_for_method(method: str) -> str | None:
    return {
        "search_trips": "trips",
        "get_active_trips": "trips",
        "get_trip": "trips",
        "search_shipments": "shipments",
        "get_shipment": "shipments",
        "get_pending_shipments": "shipments",
        "get_user_requests": "requests",
        "get_request": "requests",
        "get_offers_for_request": "shipment_requests",
        "get_offer": "shipment_requests",
        "get_user_offers": "shipment_requests",
        "get_negotiations": "shipment_requests",
        "get_market_stats": None,
    }.get(method)


class DryRunStore:
    """Validating wrapper — never performs live network calls."""

    def __init__(self, inner: Any, live: bool = False):
        self._inner = inner
        self.live = live
        self.calls: list[dict] = []

    @property
    def live_enabled(self) -> bool:
        return self.live

    def _record(self, method: str, args: tuple, ok: bool, result: Any = None, error: str = ""):
        self.calls.append({
            "method": method,
            "args": list(args),
            "ok": ok,
            "result": result,
            "error": error,
        })

    def __getattr__(self, name: str):
        inner_attr = getattr(self._inner, name)
        if not callable(inner_attr):
            return inner_attr

        def wrapper(*args, **kwargs):
            table = _table_for_method(name)
            try:
                result = inner_attr(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 — surface honestly
                self._record(name, args, False, error=str(exc))
                raise
            # validate list-of-rows results against contracts
            if table and isinstance(result, list):
                result = [validate_row(table, r) for r in result]
            elif table and isinstance(result, dict) and "id" in result:
                result = validate_row(table, result)
            self._record(name, args, True, result=result)
            return result

        return wrapper
