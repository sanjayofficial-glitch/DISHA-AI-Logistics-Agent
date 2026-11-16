"""Seed CLI — loads the synthetic demo dataset into the local SQLite store.

Usage:
    python -m app.seed.cli         # seed if empty (idempotent)
    python -m app.seed.cli --reset # wipe and reseed
    python -m app.seed.cli --status
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import settings  # noqa: E402
from app.database import SQLiteStore, utcnow  # noqa: E402
from app.seed.demo_data import (  # noqa: E402
    NOTIFICATIONS,
    OFFERS,
    REQUESTS,
    SHIPMENTS,
    TRIPS,
)


def seed(store: SQLiteStore, reset: bool = False) -> dict:
    if reset:
        for table in ("shipment_requests", "requests", "shipments", "trips",
                      "notifications", "facts", "events"):
            store._exec(f"DELETE FROM {table}")
    stats = {"trips": 0, "shipments": 0, "requests": 0, "offers": 0, "notifications": 0}

    count = store._q1("SELECT COUNT(*) c FROM trips")["c"]
    if count == 0:
        for t in TRIPS:
            store._exec(
                "INSERT INTO trips (id, transporter_user_id, origin_city, destination_city, "
                "departure_date, capacity_tonnes, price_per_tonne, vehicle_type, reliability_score, "
                "status, note, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8],
                 "active", "[DEMO] synthetic trip", "synthetic_seed_data"),
            )
            stats["trips"] += 1

    count = store._q1("SELECT COUNT(*) c FROM shipments")["c"]
    if count == 0:
        for s in SHIPMENTS:
            store._exec(
                "INSERT INTO shipments (id, shipper_user_id, origin_city, destination_city, "
                "pickup_date, weight_tonnes, goods, vehicle_type, budget_inr, status, note, source) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9],
                 "[DEMO] synthetic shipment", "synthetic_seed_data"),
            )
            stats["shipments"] += 1

    count = store._q1("SELECT COUNT(*) c FROM requests")["c"]
    if count == 0:
        for r in REQUESTS:
            created = utcnow()
            confirmed = r[10] if r[10] else None
            store._exec(
                "INSERT INTO requests (id, shipper_user_id, origin_city, destination_city, goods, "
                "weight_tonnes, vehicle_type, pickup_date, budget_inr, status, created_at, confirmed_at, "
                "note, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9],
                 created, confirmed, "[DEMO] synthetic request", "synthetic_seed_data"),
            )
            stats["requests"] += 1

    count = store._q1("SELECT COUNT(*) c FROM shipment_requests")["c"]
    if count == 0:
        for o in OFFERS:
            store._exec(
                "INSERT INTO shipment_requests (id, request_id, transporter_user_id, trip_id, "
                "price_inr, status, created_at, decided_at, note, source) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (o[0], o[1], o[2], o[3], o[4], o[5], utcnow(), utcnow(),
                 "[DEMO] synthetic offer", "synthetic_seed_data"),
            )
            stats["offers"] += 1

    count = store._q1("SELECT COUNT(*) c FROM notifications")["c"]
    if count == 0:
        for idx, n in enumerate(NOTIFICATIONS, start=1):
            store._exec(
                "INSERT INTO notifications (id, user_id, type, title, body, read, created_at) "
                "VALUES (?,?,?,?,?,0,?)",
                (f"NOTIF-SEED-{idx:04d}", n[0], n[1], n[2], n[3], utcnow()),
            )
            stats["notifications"] += 1

    return stats


def main() -> None:
    store = SQLiteStore(settings.db_path)
    args = sys.argv[1:]
    if "--status" in args:
        for table in ("trips", "shipments", "requests", "shipment_requests", "notifications"):
            c = store._q1(f"SELECT COUNT(*) c FROM {table}")["c"]
            print(f"{table}: {c}")
        return
    reset = "--reset" in args
    stats = seed(store, reset=reset)
    for k, v in stats.items():
        print(f"{k}: {v} seeded")


if __name__ == "__main__":
    main()
