"""Storage layer for DISHA.

Two implementations of `MarketplaceStore`:
  * SQLiteStore  — local demo store (default, synthetic seed data), used when
                    no Supabase project is configured. Everything carries an
                    explicit synthetic marker.
  * SupabaseStore — talks to the real LoadSaathi Supabase tables using the
                    caller's JWT (apikey + Authorization: Bearer) so existing
                    RLS stays the authorization boundary. Activated when
                    SUPABASE_URL + SUPABASE_ANON_KEY are set.

Both implement the same query/write contract so switching is a .env change.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Protocol

import httpx

from .config import settings


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _norm_city(city: str | None) -> str:
    """Strict, safe normalization. Anything non-text becomes '' (never SQL)."""
    if not city or not isinstance(city, str):
        return ""
    return city.strip().lower()


class MarketplaceStore(Protocol):
    def search_trips(self, origin: str, destination: str, limit: int | None = None) -> list[dict]: ...
    def search_shipments(self, origin: str, destination: str, limit: int | None = None) -> list[dict]: ...
    def get_market_stats(self) -> dict: ...
    def create_shipment_request(self, payload: dict) -> dict: ...
    def create_transporter_offer(self, payload: dict) -> dict: ...
    def send_notification(self, user_id: str, type_: str, title: str, body: str) -> dict: ...
    def accept_offer(self, offer_id: str) -> dict: ...
    def confirm_request(self, request_id: str) -> dict: ...
    def get_user_requests(self, user_id: str) -> list[dict]: ...
    def get_user_offers(self, user_id: str) -> list[dict]: ...
    def get_pending_shipments(self) -> list[dict]: ...
    def get_shipment(self, shipment_id: str) -> dict | None: ...
    def get_trip(self, trip_id: str) -> dict | None: ...
    def get_active_trips(self, limit: int = 100) -> list[dict]: ...
    def get_request(self, request_id: str) -> dict | None: ...
    def get_offer(self, offer_id: str) -> dict | None: ...
    def register_vehicle_availability(self, payload: dict) -> dict: ...
    def get_offers_for_request(self, request_id: str) -> list[dict]: ...
    def make_counter_offer(self, payload: dict) -> dict: ...
    def get_negotiations(self, request_id: str) -> list[dict]: ...


SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    id TEXT PRIMARY KEY,
    transporter_user_id TEXT NOT NULL,
    origin_city TEXT NOT NULL,
    destination_city TEXT NOT NULL,
    departure_date TEXT,
    capacity_tonnes REAL,
    price_per_tonne REAL,
    vehicle_type TEXT,
    reliability_score REAL DEFAULT 0.8,
    status TEXT DEFAULT 'active',
    note TEXT DEFAULT '',
    source TEXT DEFAULT 'synthetic_seed_data'
);
CREATE TABLE IF NOT EXISTS shipments (
    id TEXT PRIMARY KEY,
    shipper_user_id TEXT NOT NULL,
    origin_city TEXT NOT NULL,
    destination_city TEXT NOT NULL,
    pickup_date TEXT,
    weight_tonnes REAL,
    goods TEXT,
    vehicle_type TEXT,
    budget_inr REAL,
    status TEXT DEFAULT 'pending',
    note TEXT DEFAULT '',
    source TEXT DEFAULT 'synthetic_seed_data'
);
CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY,
    shipper_user_id TEXT NOT NULL,
    origin_city TEXT NOT NULL,
    destination_city TEXT NOT NULL,
    goods TEXT,
    weight_tonnes REAL,
    vehicle_type TEXT,
    pickup_date TEXT,
    budget_inr REAL,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    confirmed_at TEXT,
    note TEXT DEFAULT '',
    source TEXT DEFAULT 'synthetic_seed_data'
);
CREATE TABLE IF NOT EXISTS shipment_requests (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    transporter_user_id TEXT NOT NULL,
    trip_id TEXT,
    price_inr REAL,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    decided_at TEXT,
    note TEXT DEFAULT '',
    source TEXT DEFAULT 'synthetic_seed_data'
);
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT,
    title TEXT,
    body TEXT,
    read INTEGER DEFAULT 0,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT,
    user_id TEXT,
    node TEXT,
    status TEXT,
    payload_summary TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS negotiations (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    offer_id TEXT,
    party_user_id TEXT NOT NULL,
    amount_inr REAL NOT NULL,
    message TEXT DEFAULT '',
    status TEXT DEFAULT 'counter',
    created_at TEXT,
    source TEXT DEFAULT 'synthetic_seed_data'
);
CREATE INDEX IF NOT EXISTS idx_trips_cities ON trips(origin_city, destination_city);
CREATE INDEX IF NOT EXISTS idx_shipments_cities ON shipments(origin_city, destination_city);
CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id, thread_id);
CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id);
"""


class SQLiteStore:
    """Local demo store. Every returned write carries synthetic markers."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # -- helpers ----------------------------------------------------------
    def _q(self, sql: str, params: tuple = ()) -> list[dict]:
        cur = self._conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def _q1(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self._q(sql, params)
        return rows[0] if rows else None

    def _exec(self, sql: str, params: tuple = ()) -> None:
        self._conn.execute(sql, params)
        self._conn.commit()

    # -- reads ------------------------------------------------------------
    def search_trips(self, origin: str, destination: str, limit: int | None = None) -> list[dict]:
        o, d = _norm_city(origin), _norm_city(destination)
        limit = limit or settings.search_limit
        rows = self._q(
            "SELECT * FROM trips WHERE status='active' AND origin_city=? AND destination_city=? "
            "ORDER BY departure_date LIMIT ?",
            (o, d, limit),
        )
        return [dict(r) for r in rows]

    def get_active_trips(self, limit: int = 100) -> list[dict]:
        return self._q(
            "SELECT * FROM trips WHERE status='active' ORDER BY departure_date LIMIT ?",
            (limit,),
        )

    def search_shipments(self, origin: str, destination: str, limit: int | None = None) -> list[dict]:
        o, d = _norm_city(origin), _norm_city(destination)
        limit = limit or settings.search_limit
        rows = self._q(
            "SELECT * FROM shipments WHERE status='pending' AND origin_city=? AND destination_city=? "
            "ORDER BY pickup_date LIMIT ?",
            (o, d, limit),
        )
        return [dict(r) for r in rows]

    def get_market_stats(self) -> dict:
        active_trips = self._q1("SELECT COUNT(*) c FROM trips WHERE status='active'")["c"]
        pending_shipments = self._q1("SELECT COUNT(*) c FROM shipments WHERE status='pending'")["c"]
        pending_requests = self._q1("SELECT COUNT(*) c FROM requests WHERE status='pending'")["c"]
        return {
            "active_trips": active_trips,
            "pending_shipments": pending_shipments,
            "pending_requests": pending_requests,
            "is_demo": True,
            "source": "synthetic_seed_data",
        }

    # -- writes -----------------------------------------------------------
    def create_shipment_request(self, payload: dict) -> dict:
        rid = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        row = {
            "id": rid,
            "shipper_user_id": payload["shipper_user_id"],
            "origin_city": _norm_city(payload.get("origin")),
            "destination_city": _norm_city(payload.get("destination")),
            "goods": str(payload.get("goods") or ""),
            "weight_tonnes": payload.get("weight_tonnes"),
            "vehicle_type": str(payload.get("vehicle_type") or ""),
            "pickup_date": str(payload.get("pickup_date") or ""),
            "budget_inr": payload.get("budget_inr"),
            "status": "pending",
            "created_at": utcnow(),
            "confirmed_at": None,
            "note": "[DEMO] synthetic request",
            "source": "synthetic_seed_data",
        }
        self._exec(
            "INSERT INTO requests (id, shipper_user_id, origin_city, destination_city, goods, "
            "weight_tonnes, vehicle_type, pickup_date, budget_inr, status, created_at, confirmed_at, "
            "note, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            tuple(row[k] for k in ("id", "shipper_user_id", "origin_city", "destination_city", "goods",
                                  "weight_tonnes", "vehicle_type", "pickup_date", "budget_inr",
                                  "status", "created_at", "confirmed_at", "note", "source")),
        )
        return self.get_request(rid) or row

    def create_transporter_offer(self, payload: dict) -> dict:
        oid = f"OFF-{uuid.uuid4().hex[:8].upper()}"
        row = {
            "id": oid,
            "request_id": payload["request_id"],
            "transporter_user_id": payload["transporter_user_id"],
            "trip_id": payload.get("trip_id"),
            "price_inr": payload.get("price_inr"),
            "status": "pending",
            "created_at": utcnow(),
            "decided_at": None,
            "note": "[DEMO] synthetic offer",
            "source": "synthetic_seed_data",
        }
        self._exec(
            "INSERT INTO shipment_requests (id, request_id, transporter_user_id, trip_id, price_inr, "
            "status, created_at, decided_at, note, source) VALUES (?,?,?,?,?,?,?,?,?,?)",
            tuple(row[k] for k in ("id", "request_id", "transporter_user_id", "trip_id", "price_inr",
                                  "status", "created_at", "decided_at", "note", "source")),
        )
        return self.get_offer(oid) or row

    def send_notification(self, user_id: str, type_: str, title: str, body: str) -> dict:
        nid = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
        row = {"id": nid, "user_id": user_id, "type": type_, "title": title,
               "body": body, "read": 0, "created_at": utcnow()}
        self._exec(
            "INSERT INTO notifications (id, user_id, type, title, body, read, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (nid, user_id, type_, title, body, 0, row["created_at"]),
        )
        return row

    def accept_offer(self, offer_id: str) -> dict:
        offer = self.get_offer(offer_id)
        if not offer:
            raise KeyError("offer not found")
        if offer["status"] != "pending":
            raise ValueError("only pending offers can be accepted")
        self._exec("UPDATE shipment_requests SET status='accepted', decided_at=? WHERE id=?",
                   (utcnow(), offer_id))
        return self.get_offer(offer_id) or offer

    def confirm_request(self, request_id: str) -> dict:
        req = self.get_request(request_id)
        if not req:
            raise KeyError("request not found")
        if req["status"] != "pending":
            raise ValueError("only pending requests can be confirmed")
        now = utcnow()
        self._exec("UPDATE requests SET status='confirmed', confirmed_at=? WHERE id=?", (now, request_id))
        return self.get_request(request_id) or req

    def get_user_requests(self, user_id: str) -> list[dict]:
        return self._q("SELECT * FROM requests WHERE shipper_user_id=? ORDER BY created_at DESC", (user_id,))

    def get_user_offers(self, user_id: str) -> list[dict]:
        return self._q(
            "SELECT so.*, r.origin_city, r.destination_city, r.goods, r.weight_tonnes, r.pickup_date "
            "FROM shipment_requests so LEFT JOIN requests r ON r.id=so.request_id "
            "WHERE so.transporter_user_id=? ORDER BY so.created_at DESC",
            (user_id,),
        )

    def get_pending_shipments(self) -> list[dict]:
        return self._q(
            "SELECT s.*, (SELECT COUNT(*) FROM shipment_requests so WHERE so.request_id=s.id AND so.status='pending') "
            "AS offers_pending FROM shipments s WHERE s.status='pending' ORDER BY s.pickup_date",
        )

    def get_shipment(self, shipment_id: str) -> dict | None:
        return self._q1("SELECT * FROM shipments WHERE id=?", (shipment_id,))

    def get_trip(self, trip_id: str) -> dict | None:
        return self._q1("SELECT * FROM trips WHERE id=?", (trip_id,))

    def get_request(self, request_id: str) -> dict | None:
        return self._q1("SELECT * FROM requests WHERE id=?", (request_id,))

    def get_offer(self, offer_id: str) -> dict | None:
        return self._q1("SELECT * FROM shipment_requests WHERE id=?", (offer_id,))

    def register_vehicle_availability(self, payload: dict) -> dict:
        """Publish a vehicle availability as an ACTIVE demo trip row."""
        tid = f"TRIP-{uuid.uuid4().hex[:8].upper()}"
        row = {
            "id": tid,
            "transporter_user_id": payload["transporter_user_id"],
            "origin_city": _norm_city(payload.get("origin")),
            "destination_city": _norm_city(payload.get("destination")),
            "departure_date": str(payload.get("pickup_date") or ""),
            "capacity_tonnes": payload.get("capacity_tonnes"),
            "price_per_tonne": None,
            "vehicle_type": str(payload.get("vehicle_type") or "open_body"),
            "reliability_score": 0.8,
            "status": "active",
            "note": "[DEMO] synthetic vehicle availability",
            "source": "synthetic_seed_data",
        }
        self._exec(
            "INSERT INTO trips (id, transporter_user_id, origin_city, destination_city, "
            "departure_date, capacity_tonnes, price_per_tonne, vehicle_type, reliability_score, "
            "status, note, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            tuple(row[k] for k in (
                "id", "transporter_user_id", "origin_city", "destination_city",
                "departure_date", "capacity_tonnes", "price_per_tonne",
                "vehicle_type", "reliability_score", "status", "note", "source",
            )),
        )
        return self.get_trip(tid) or row

    def get_offers_for_request(self, request_id: str) -> list[dict]:
        return self._q(
            "SELECT * FROM shipment_requests WHERE request_id=? ORDER BY created_at ASC",
            (request_id,),
        )

    def make_counter_offer(self, payload: dict) -> dict:
        nid = f"NEG-{uuid.uuid4().hex[:8].upper()}"
        row = {
            "id": nid,
            "request_id": payload["request_id"],
            "offer_id": payload.get("offer_id"),
            "party_user_id": payload["party_user_id"],
            "amount_inr": payload.get("amount_inr"),
            "message": str(payload.get("message") or ""),
            "status": "counter",
            "created_at": utcnow(),
            "source": "synthetic_seed_data",
        }
        self._exec(
            "INSERT INTO negotiations (id, request_id, offer_id, party_user_id, amount_inr, "
            "message, status, created_at, source) VALUES (?,?,?,?,?,?,?,?,?)",
            tuple(row[k] for k in (
                "id", "request_id", "offer_id", "party_user_id", "amount_inr",
                "message", "status", "created_at", "source",
            )),
        )
        return row

    def get_negotiations(self, request_id: str) -> list[dict]:
        return self._q(
            "SELECT * FROM negotiations WHERE request_id=? ORDER BY created_at ASC",
            (request_id,),
        )


class SupabaseStore:
    """Read/write against the real LoadSaathi Supabase tables with the
    caller's JWT. RLS remains the authorization boundary — we never use a
    service-role key. `user_token` is supplied per request (never stored).
    """

    def __init__(self, url: str, anon_key: str, user_token: str):
        self.url = url.rstrip("/")
        self.anon_key = anon_key
        self.token = user_token
        self._client = httpx.Client(
            base_url=self.url,
            headers={
                "apikey": self.anon_key,
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=settings.provider_timeout_s,
        )

    def _rest(self, table: str, params: dict | None = None) -> list[dict]:
        resp = self._client.get(f"/rest/v1/{table}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _insert(self, table: str, row: dict) -> dict:
        resp = self._client.post(f"/rest/v1/{table}", json=row, params={"return": "representation", "prefer": "return=representation"})
        resp.raise_for_status()
        return resp.json()[0]

    def _update(self, table: str, row_id: str, updates: dict) -> dict:
        resp = self._client.patch(
            f"/rest/v1/{table}", json=updates, params={"id": f"eq.{row_id}", "return": "representation", "prefer": "return=representation"}
        )
        resp.raise_for_status()
        return resp.json()[0]

    def search_trips(self, origin: str, destination: str, limit: int | None = None) -> list[dict]:
        limit = limit or settings.search_limit
        return self._rest("trips", {
            "status": "eq.active",
            "origin_city": f"eq.{_norm_city(origin)}",
            "destination_city": f"eq.{_norm_city(destination)}",
            "order": "departure_date",
            "limit": str(limit),
        })

    def get_active_trips(self, limit: int = 100) -> list[dict]:
        return self._rest("trips", {
            "status": "eq.active", "order": "departure_date", "limit": str(limit),
        })

    def search_shipments(self, origin: str, destination: str, limit: int | None = None) -> list[dict]:
        limit = limit or settings.search_limit
        return self._rest("shipments", {
            "status": "eq.pending",
            "origin_city": f"eq.{_norm_city(origin)}",
            "destination_city": f"eq.{_norm_city(destination)}",
            "order": "pickup_date",
            "limit": str(limit),
        })

    def get_market_stats(self) -> dict:
        return {
            "active_trips": len(self._rest("trips", {"status": "eq.active", "select": "id", "limit": "1000"})),
            "pending_shipments": len(self._rest("shipments", {"status": "eq.pending", "select": "id", "limit": "1000"})),
            "pending_requests": len(self._rest("requests", {"status": "eq.pending", "select": "id", "limit": "1000"})),
            "is_demo": False,
            "source": "loadsaathi_supabase",
        }

    def create_shipment_request(self, payload: dict) -> dict:
        return self._insert("requests", {
            "shipper_user_id": payload["shipper_user_id"],
            "origin_city": _norm_city(payload.get("origin")),
            "destination_city": _norm_city(payload.get("destination")),
            "goods": str(payload.get("goods") or ""),
            "weight_tonnes": payload.get("weight_tonnes"),
            "vehicle_type": str(payload.get("vehicle_type") or ""),
            "pickup_date": str(payload.get("pickup_date") or ""),
            "budget_inr": payload.get("budget_inr"),
            "status": "pending",
            "created_at": utcnow(),
        })

    def create_transporter_offer(self, payload: dict) -> dict:
        return self._insert("shipment_requests", {
            "request_id": payload["request_id"],
            "transporter_user_id": payload["transporter_user_id"],
            "trip_id": payload.get("trip_id"),
            "price_inr": payload.get("price_inr"),
            "status": "pending",
            "created_at": utcnow(),
        })

    def send_notification(self, user_id: str, type_: str, title: str, body: str) -> dict:
        return self._insert("notifications", {
            "user_id": user_id, "type": type_, "title": title,
            "body": body, "read": False, "created_at": utcnow(),
        })

    def accept_offer(self, offer_id: str) -> dict:
        return self._update("shipment_requests", offer_id, {"status": "accepted", "decided_at": utcnow()})

    def confirm_request(self, request_id: str) -> dict:
        return self._update("requests", request_id, {"status": "confirmed", "confirmed_at": utcnow()})

    def get_user_requests(self, user_id: str) -> list[dict]:
        return self._rest("requests", {"shipper_user_id": f"eq.{user_id}", "order": "created_at.desc"})

    def get_user_offers(self, user_id: str) -> list[dict]:
        return self._rest("shipment_requests", {"transporter_user_id": f"eq.{user_id}", "order": "created_at.desc"})

    def get_pending_shipments(self) -> list[dict]:
        return self._rest("shipments", {"status": "eq.pending", "order": "pickup_date"})

    def get_shipment(self, shipment_id: str) -> dict | None:
        rows = self._rest("shipments", {"id": f"eq.{shipment_id}"})
        return rows[0] if rows else None

    def get_trip(self, trip_id: str) -> dict | None:
        rows = self._rest("trips", {"id": f"eq.{trip_id}"})
        return rows[0] if rows else None

    def get_request(self, request_id: str) -> dict | None:
        rows = self._rest("requests", {"id": f"eq.{request_id}"})
        return rows[0] if rows else None

    def get_offer(self, offer_id: str) -> dict | None:
        rows = self._rest("shipment_requests", {"id": f"eq.{offer_id}"})
        return rows[0] if rows else None

    def register_vehicle_availability(self, payload: dict) -> dict:
        # Live Supabase trip publishing is intentionally NOT wired for the
        # competition demo; availability publishing is demo SQLite only.
        raise NotImplementedError(
            "register_vehicle_availability: live Supabase path not wired "
            "(demo SQLite only)"
        )

    def get_offers_for_request(self, request_id: str) -> list[dict]:
        return self._rest("shipment_requests", {
            "request_id": f"eq.{request_id}", "order": "created_at",
        })

    def make_counter_offer(self, payload: dict) -> dict:
        raise NotImplementedError(
            "make_counter_offer: live Supabase negotiation schema absent "
            "(demo SQLite only)"
        )

    def get_negotiations(self, request_id: str) -> list[dict]:
        raise NotImplementedError(
            "get_negotiations: live Supabase negotiation schema absent "
            "(demo SQLite only)"
        )


def get_store(user_token: str | None = None) -> MarketplaceStore:
    """Return the active store. With a configured Supabase project, every
    call passes the caller's JWT; otherwise the SQLite demo store is used."""
    if settings.supabase_url and settings.supabase_anon_key:
        if not user_token:
            from .auth import verify_token
            raise ValueError("user token required for Supabase store")
        return SupabaseStore(settings.supabase_url, settings.supabase_anon_key, user_token)
    return SQLiteStore()
