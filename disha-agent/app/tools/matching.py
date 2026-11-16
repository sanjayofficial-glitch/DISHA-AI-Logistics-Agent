"""Deterministic matching engine — pure Python, never the LLM.

Weights (per playbook): route 35%, capacity 25%, price 20%, date 10%,
reliability 10%. Every factor is normalized 0..1 and documented. The engine
never invents data: it only scores rows returned by the store.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

W_ROUTE = 0.35
W_CAPACITY = 0.25
W_PRICE = 0.20
W_DATE = 0.10
W_RELIABILITY = 0.10


def _parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _route_score(row: dict, origin: str, destination: str) -> tuple[float, str]:
    o = str(row.get("origin_city") or "").strip().lower()
    d = str(row.get("destination_city") or "").strip().lower()
    want_o = origin.strip().lower()
    want_d = destination.strip().lower()
    if o == want_o and d == want_d:
        return 1.0, "exact origin+destination match"
    if o == want_o:
        return 0.55, "origin matches; destination differs"
    if d == want_d:
        return 0.45, "destination matches; origin differs"
    return 0.0, "route does not match"


def _capacity_score(row: dict, needed: float | None, mode: str) -> tuple[float, str]:
    if mode == "find_truck":
        cap = row.get("capacity_tonnes")
        if cap is None or needed is None:
            return 0.5, "capacity not comparable (missing data)"
        cap = float(cap)
        if cap >= needed:
            return 1.0, f"capacity {cap:g}t fits {needed:g}t"
        return round(cap / needed, 3), f"capacity {cap:g}t < {needed:g}t (partial fit)"
    # find_load: shipment weight vs truck capacity (unknown here -> neutral)
    return 0.5, "truck capacity not provided; neutral"


def _price_score(row: dict, budget: float | None, mode: str,
                 weight: float | None) -> tuple[float, str]:
    if mode == "find_truck":
        rate = row.get("price_per_tonne")
        if rate is None:
            return 0.5, "no price listed for this trip"
        rate = float(rate)
        if budget is None:
            return 0.5, f"rate ₹{rate:,.0f}/tonne; no budget provided for comparison"
        est = rate * (weight or 1.0)
        diff = abs(est - budget) / max(budget, 1.0)
        fit = round(max(0.0, 1.0 - min(diff, 1.0)), 3)
        return fit, f"est. ₹{est:,.0f} vs budget ₹{budget:,.0f}"
    budget_row = row.get("budget_inr")
    if budget_row is None:
        return 0.5, "no budget listed for this load"
    return 0.5, f"load budget ₹{float(budget_row):,.0f}; offer price to be set"


def _date_score(row: dict, desired: str | None) -> tuple[float, str]:
    d = _parse_date(desired)
    r = _parse_date(str(row.get("pickup_date") or row.get("departure_date") or ""))
    if not d or not r:
        return 0.5, "date not comparable (missing data)"
    diff = abs((r - d).days)
    fit = max(0.0, 1.0 - 0.2 * diff)
    return round(fit, 3), f"date {r.isoformat()} vs desired {d.isoformat()} ({diff}d away)"


def _reliability_score(row: dict) -> tuple[float, str]:
    s = row.get("reliability_score")
    if s is None:
        return 0.5, "reliability unknown (neutral)"
    return round(float(s), 3), f"transporter reliability {float(s):.2f}"


def score_candidate(row: dict, intent: dict, mode: str) -> dict:
    """Score one candidate row. `mode` is find_truck | find_load."""
    origin = intent.get("origin") or ""
    destination = intent.get("destination") or ""
    weight = intent.get("weight_tonnes")
    budget = intent.get("budget_inr")
    date_ = intent.get("pickup_date")

    r_route, n_route = _route_score(row, origin, destination)
    r_cap, n_cap = _capacity_score(row, weight, mode)
    r_price, n_price = _price_score(row, budget, mode, weight)
    r_date, n_date = _date_score(row, date_)
    r_rel, n_rel = _reliability_score(row)

    total = round(
        W_ROUTE * r_route
        + W_CAPACITY * r_cap
        + W_PRICE * r_price
        + W_DATE * r_date
        + W_RELIABILITY * r_rel,
        3,
    )

    return {
        "factors": {
            "route": {"score": r_route, "note": n_route},
            "capacity": {"score": r_cap, "note": n_cap},
            "price": {"score": r_price, "note": n_price},
            "date": {"score": r_date, "note": n_date},
            "reliability": {"score": r_rel, "note": n_rel},
        },
        "total_score": total,
        "explanation": (
            f"Route {r_route:.2f}·0.35 + capacity {r_cap:.2f}·0.25 + "
            f"price {r_price:.2f}·0.20 + date {r_date:.2f}·0.10 + "
            f"reliability {r_rel:.2f}·0.10 = {total:.3f}"
        ),
    }


def rank_candidates(rows: list[dict], intent: dict, mode: str) -> list[dict]:
    """Rank rows by total score, each with per-factor explanation."""
    out = []
    for row in rows:
        scored = score_candidate(row, intent, mode)
        candidate = {
            "id": row.get("id"),
            "source_table": "trips" if mode == "find_truck" else "shipments",
            "origin_city": row.get("origin_city"),
            "destination_city": row.get("destination_city"),
            "total_score": scored["total_score"],
            "factors": scored["factors"],
            "explanation": scored["explanation"],
            "extra": {k: v for k, v in row.items() if k not in ("origin_city", "destination_city", "id")},
            "is_demo": True,
            "source": "synthetic_seed_data",
        }
        out.append(candidate)
    out.sort(key=lambda c: c["total_score"], reverse=True)
    return out
