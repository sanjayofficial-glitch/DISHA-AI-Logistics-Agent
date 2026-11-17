"""AgentService — drives the LangGraph workflow per HTTP request.

Ownership model:
  * The verified user id lives in graph state (needed for isolation checks).
  * The raw JWT is request-scoped runtime context (contextvars), refreshed and
    revalidated on /approve. It is never persisted to checkpoints.
"""
from __future__ import annotations

import datetime as dt
import uuid

from . import events as events_mod
from .config import settings
from .context import clear_request_context, set_request_context
from .graph import create_graph
from .providers import ProviderError


def _approval_expired(pending_action: dict) -> bool:
    """True when the pending action is older than approval_expires_minutes.
    Unparseable timestamps are treated as not expired (safe default)."""
    raw = pending_action.get("created_at")
    if not raw:
        return False
    try:
        created = dt.datetime.fromisoformat(raw)
        if created.tzinfo is None:
            created = created.replace(tzinfo=dt.timezone.utc)
        age = dt.datetime.now(dt.timezone.utc) - created
        return age > dt.timedelta(minutes=settings.approval_expires_minutes)
    except (ValueError, TypeError):
        return False


class AgentService:
    def __init__(self) -> None:
        self.graph = None
        self._events = events_mod.EventStore()

    def _ensure_graph(self):
        if self.graph is None:
            self.graph = create_graph()
        return self.graph

    def _config(self, thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    def chat(self, token: str, message: str, thread_id: str | None = None) -> dict:
        from .auth import verify_token

        claims = verify_token(token)
        user_id = claims.sub
        tid = thread_id or f"thr-{uuid.uuid4().hex[:12]}"
        set_request_context(user_id, token)
        try:
            graph = self._ensure_graph()
            initial = {"thread_id": tid, "user_id": user_id, "message": message}
            try:
                result = graph.invoke(initial, self._config(tid))
            except Exception as exc:  # langgraph versions may raise GraphInterrupt
                if "interrupt" in exc.__class__.__name__.lower():
                    result = graph.get_state(self._config(tid)).values
                else:
                    raise
            return self._respond(tid, user_id, result)
        except ProviderError as exc:
            return {
                "thread_id": tid,
                "status": "error",
                "reply": f"AI provider unavailable. {exc}",
                "provider": "unavailable",
                "approval_required": False,
                "pending_action": None,
            }
        finally:
            clear_request_context()

    def approve(self, token: str, thread_id: str) -> dict:
        from .auth import verify_token

        claims = verify_token(token)
        user_id = claims.sub
        graph = self._ensure_graph()
        state = graph.get_state(self._config(thread_id))
        if not state or not state.values:
            return {"error": "thread not found", "status": "error"}
        owner = state.values.get("user_id")
        if owner != user_id:
            return {"error": "forbidden: not your thread", "status": "forbidden"}
        pa = state.values.get("pending_action")
        if not pa:
            return {"error": "nothing to approve", "status": "error"}
        if _approval_expired(pa):
            graph.update_state(
                self._config(thread_id),
                {
                    "approval_required": False,
                    "pending_action": None,
                    "status": "done",
                    "reply": "Approval expired — nothing was written. Please ask Disha again.",
                },
            )
            self._events.append(thread_id, user_id, "coordinate", "expired",
                                "approval expired before approval")
            return {"thread_id": thread_id, "status": "expired",
                    "reply": "Approval expired — nothing was written.",
                    "approval_required": False, "pending_action": None}
        set_request_context(user_id, token)
        try:
            result = graph.invoke(None, self._config(thread_id))
            return self._respond(thread_id, user_id, result)
        except ProviderError as exc:
            return {"status": "error", "reply": f"AI provider unavailable. {exc}"}
        finally:
            clear_request_context()

    def reject(self, token: str, thread_id: str) -> dict:
        from .auth import verify_token

        claims = verify_token(token)
        user_id = claims.sub
        graph = self._ensure_graph()
        state = graph.get_state(self._config(thread_id))
        if not state or not state.values:
            return {"error": "thread not found", "status": "error"}
        if state.values.get("user_id") != user_id:
            return {"error": "forbidden: not your thread", "status": "forbidden"}
        if not state.values.get("pending_action"):
            return {"error": "nothing to reject", "status": "error"}
        graph.update_state(
            self._config(thread_id),
            {
                "approval_required": False,
                "pending_action": None,
                "status": "done",
                "reply": "Action rejected. Nothing was written.",
            },
        )
        self._events.append(thread_id, user_id, "coordinate", "rejected", "user rejected the pending action")
        return {"thread_id": thread_id, "status": "done", "reply": "Action rejected. Nothing was written.",
                "approval_required": False, "pending_action": None}

    def thread_events(self, token: str, thread_id: str) -> list[dict] | dict:
        from .auth import verify_token

        user_id = verify_token(token).sub
        graph = self._ensure_graph()
        state = graph.get_state(self._config(thread_id))
        if state and state.values and state.values.get("user_id") != user_id:
            return {"error": "forbidden", "status": "forbidden"}
        if state is None or not state.values:
            return {"error": "thread not found", "status": "error"}
        return self._events.list_for_thread(thread_id)

    def list_threads(self, token: str) -> list[str]:
        from .auth import verify_token

        user_id = verify_token(token).sub
        return self._events.thread_ids_for_user(user_id)

    def pending_approvals(self, token: str) -> list[dict]:
        """Owner-scoped list of threads waiting on human approval (from the
        LangGraph checkpointer state, read-only)."""
        from .auth import verify_token

        user_id = verify_token(token).sub
        graph = self._ensure_graph()
        out: list[dict] = []
        for tid in self._events.thread_ids_for_user(user_id)[:50]:
            state = graph.get_state(self._config(tid))
            if not state or not state.values:
                continue
            values = state.values
            if values.get("user_id") != user_id:
                continue
            pa = values.get("pending_action")
            if values.get("approval_required") and pa:
                out.append({
                    "thread_id": tid,
                    "type": pa.get("type"),
                    "summary": pa.get("summary", ""),
                    "created_at": pa.get("created_at", ""),
                })
        return out

    def metrics(self) -> dict:
        return self._events.metrics()

    def _respond(self, thread_id: str, user_id: str, result: dict) -> dict:
        pending = result.get("pending_action")
        return {
            "thread_id": thread_id,
            "status": result.get("status", "ok"),
            "reply": result.get("reply", ""),
            "provider": result.get("provider", ""),
            "approval_required": bool(result.get("approval_required")),
            "pending_action": pending,
            "candidates": result.get("candidates", [])[:5],
            "search_mode": result.get("search_mode"),
            "demo_mode": settings.demo_mode,
        }


service = AgentService()
