"""Tool registry — every dat uses a Pydantic input schema, a timeout, an
execution log entry, and a read-only permission flag. Handlers receive the
request-scoped store (caller JWT already applied for Supabase mode).
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field


class ToolResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ok: bool = False
    tool: str = ""
    data: Any = None
    error: str | None = None
    is_demo: bool = True
    source: str = "synthetic_seed_data"
    duration_s: float = 0.0
    ts: str = ""


class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: type[BaseModel],
        handler: Callable[[Any, dict], Any],
        read_only: bool = True,
        timeout_s: float = 10.0,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler
        self.read_only = read_only
        self.timeout_s = timeout_s

    def run(self, store: Any, raw_args: dict) -> ToolResult:
        started = dt.datetime.now(dt.timezone.utc)
        result = ToolResult(tool=self.name, ts=started.isoformat(timespec="seconds"))
        try:
            args = self.input_schema.model_validate(raw_args)
            data = self.handler(store, args.model_dump())
            result.ok = True
            result.data = data
        except Exception as exc:  # noqa: BLE001 — surfaced honestly to the UI
            result.ok = False
            result.error = f"{exc.__class__.__name__}: {exc}"
            if isinstance(exc, ValueError):
                result.error = str(exc)
        result.duration_s = round(
            (dt.datetime.now(dt.timezone.utc) - started).total_seconds(), 3
        )
        return result


_REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    _REGISTRY[tool.name] = tool
    return tool


def get_tool(name: str) -> Tool:
    return _REGISTRY[name]


def list_tools() -> list[Tool]:
    return list(_REGISTRY.values())


def all_tools_for_action(action: str) -> list[str]:
    """Map a planned intent/action to the tools it may call."""
    mapping = {
        "find_truck": ["search_trips", "get_market_stats"],
        "find_load": ["search_shipments", "get_market_stats"],
        "create_request": ["create_shipment_request"],
        "send_offer": ["create_transporter_offer"],
        "accept_offer": ["accept_offer"],
        "confirm_request": ["confirm_request"],
        "remember": ["add_memory"],
    }
    return mapping.get(action, [])
