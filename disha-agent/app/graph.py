"""LangGraph workflow — understand -> discover -> rank -> coordinate -> execute,
compiled with a SQLite checkpointer and interrupt_before=["execute"] so every
write waits for explicit human approval.
"""
from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .config import settings
from .nodes import coordinate, discover, execute, rank, understand
from .state import DishaState

_saver: SqliteSaver | None = None


def _get_saver() -> SqliteSaver:
    """Persistent checkpointer — the connection lives for the process lifetime
    so conversations survive restarts of the API worker (SQLite file)."""
    global _saver
    if _saver is None:
        conn = sqlite3.connect(str(settings.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _saver = SqliteSaver(conn)
    return _saver


def _build_graph(checkpointer):
    g = StateGraph(DishaState)
    g.add_node("understand", understand)
    g.add_node("discover", discover)
    g.add_node("rank", rank)
    g.add_node("coordinate", coordinate)
    g.add_node("execute", execute)

    g.add_edge(START, "understand")

    def after_understand(state):
        # A request for input (or an honest error) ends the turn here.
        if state.get("status") in ("needs_input", "error"):
            return END
        action = state.get("intent", {}).get("action")
        if action in ("find_truck", "find_load"):
            return "discover"
        if action in ("create_request", "send_offer", "accept_offer", "confirm_request",
                      "publish_availability", "counter_offer", "cancel_request"):
            return "coordinate"
        return END

    g.add_conditional_edges("understand", after_understand, {
        "discover": "discover",
        "coordinate": "coordinate",
        END: END,
    })
    g.add_edge("discover", "rank")
    g.add_edge("rank", "coordinate")

    def after_coordinate(state):
        if state.get("pending_action"):
            return "execute"
        return END

    g.add_conditional_edges("coordinate", after_coordinate, {
        "execute": "execute",
        END: END,
    })
    g.add_edge("execute", END)
    return g.compile(checkpointer=checkpointer, interrupt_before=["execute"])


def create_graph():
    """Return a compiled graph with a SQLite checkpointer."""
    return _build_graph(_get_saver())
