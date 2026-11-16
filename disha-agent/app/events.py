"""Event store — every node transition appends a structured event.

Phase 7 exposes these events to the Command Center UI.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import settings
from .database import utcnow


class EventStore:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT,
                user_id TEXT,
                node TEXT,
                status TEXT,
                payload_summary TEXT,
                created_at TEXT
            )"""
        )
        self._conn.commit()

    def append(self, thread_id: str, user_id: str, node: str, status: str,
               payload_summary: str = "") -> dict:
        row = {
            "thread_id": thread_id,
            "user_id": user_id,
            "node": node,
            "status": status,
            "payload_summary": payload_summary,
            "created_at": utcnow(),
        }
        cur = self._conn.execute(
            "INSERT INTO events (thread_id, user_id, node, status, payload_summary, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (thread_id, user_id, node, status, payload_summary, row["created_at"]),
        )
        self._conn.commit()
        row["id"] = cur.lastrowid
        return row

    def list_for_thread(self, thread_id: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT * FROM events WHERE thread_id=? ORDER BY id ASC", (thread_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    def list_for_user(self, user_id: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT * FROM events WHERE user_id=? ORDER BY id DESC LIMIT 500", (user_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    def thread_ids_for_user(self, user_id: str) -> list[str]:
        cur = self._conn.execute(
            "SELECT thread_id FROM events WHERE user_id=? AND thread_id IS NOT NULL "
            "GROUP BY thread_id ORDER BY MAX(id) DESC",
            (user_id,),
        )
        return [r["thread_id"] for r in cur.fetchall()]

    def metrics(self) -> dict:
        """Live metrics computed from recorded events + tables. Values that
        cannot be computed are `None` (honest)."""
        out: dict = {
            "request_to_match_seconds": None,
            "eligible_trucks_found": None,
            "offers_sent": None,
            "acceptance_rate": None,
            "time_to_booking_confirmation_seconds": None,
            "match_success_rate": None,
            "is_demo": True,
            "source": "synthetic_seed_data",
        }
        try:
            # Offers sent + acceptance rate
            offers = self._conn.execute("SELECT status FROM shipment_requests").fetchall()
            total_offers = len(offers)
            accepted = sum(1 for o in offers if o["status"] == "accepted")
            out["offers_sent"] = total_offers
            out["acceptance_rate"] = round(accepted / total_offers, 3) if total_offers else None

            # Requests: match success + time-to-confirmation
            reqs = self._conn.execute(
                "SELECT created_at, confirmed_at, status FROM requests"
            ).fetchall()
            total_reqs = len(reqs)
            confirmed_reqs = [r for r in reqs if r["confirmed_at"]]
            out["match_success_rate"] = round(len(confirmed_reqs) / total_reqs, 3) if total_reqs else None
            if confirmed_reqs:
                import datetime as dtmod
                deltas = []
                for r in confirmed_reqs:
                    try:
                        a = dtmod.datetime.fromisoformat(r["created_at"])
                        b = dtmod.datetime.fromisoformat(r["confirmed_at"])
                        deltas.append((b - a).total_seconds())
                    except (ValueError, TypeError):
                        continue
                if deltas:
                    out["time_to_booking_confirmation_seconds"] = round(sum(deltas) / len(deltas), 1)

            # Request-to-match: delta between request-created event and first rank event per thread
            rows = self._conn.execute(
                "SELECT thread_id, node, created_at FROM events "
                "WHERE node IN ('discover','rank') OR payload_summary LIKE '%request created%' "
                "ORDER BY thread_id, id"
            ).fetchall()
            per_thread: dict[str, dict] = {}
            for r in rows:
                t = r["thread_id"]
                if t not in per_thread:
                    per_thread[t] = {"created": None, "matched": None}
                if r["node"] == "rank" and per_thread[t]["matched"] is None:
                    per_thread[t]["matched"] = r["created_at"]
                if "request created" in (r["payload_summary"] or "") and per_thread[t]["created"] is None:
                    per_thread[t]["created"] = r["created_at"]
            deltas = []
            for t, v in per_thread.items():
                if v["created"] and v["matched"]:
                    try:
                        a = dtmod.datetime.fromisoformat(v["created"])
                        b = dtmod.datetime.fromisoformat(v["matched"])
                        deltas.append((b - a).total_seconds())
                    except (ValueError, TypeError):
                        continue
            if deltas:
                out["request_to_match_seconds"] = round(sum(deltas) / len(deltas), 1)
        except sqlite3.Error:
            pass
        return out
