"""Request-scoped runtime context.

The caller's JWT lives here for the duration of one HTTP request — it is
never stored in graph state or checkpoints. `require_token` refreshes it at
request entry; the /approve resume revalidates it before continuing.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_request_ctx: ContextVar[dict[str, Any] | None] = ContextVar("disha_request_ctx", default=None)


def set_request_context(user_id: str, token: str) -> None:
    _request_ctx.set({"user_id": user_id, "token": token})


def clear_request_context() -> None:
    _request_ctx.set(None)


def current_user_id() -> str:
    ctx = _request_ctx.get()
    if not ctx or not ctx.get("user_id"):
        raise RuntimeError("no request context")
    return ctx["user_id"]


def current_token() -> str:
    ctx = _request_ctx.get()
    if not ctx or not ctx.get("token"):
        raise RuntimeError("no request context")
    return ctx["token"]
