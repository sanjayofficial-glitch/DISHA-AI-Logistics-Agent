"""Partial Truckload (PTL) feasibility engine — deterministic, honest.

Given a candidate vehicle (trip) and two+ loads, evaluate whether they can
realistically travel together on the same vehicle:
  - total weight ≤ capacity (with a utilization margin)
  - route overlap: every load's origin/destination must lie on a coherent
    corridor through the vehicle's route (simplified demo corridor check)
  - date alignment: loads must fit the vehicle's departure window
  - cargo compatibility: no explicit restrictions in the demo schema, so we
    state that as an unchecked assumption
  - detour cost: combined route distance estimate with DETOUR_MULTIPLIER

This is a DEMO feasibility assessment, not a guarantee. It never invents
distances for unknown corridors.
"""
from __future__ import annotations

from .routing import CORRIDOR_KM, DETOUR_MULTIPLIER, clean_city

UTILIZATION_MARGIN = 0.95  # allow up to 95% of capacity in a combination


def _coherent_route(loads: list[dict]) -> bool:
    """All loads must share one corridor: same origin-city pivot and same
    destination-city pivot (demo simplification of route overlap)."""
    origins = {clean_city(l.get("origin_city") or "") for l in loads}
    destinations = {clean_city(l.get("destination_city") or "") for l in loads}
    if not origins or not destinations:
        return False
    return len(origins) == 1 and len(destinations) == 1


def _total_weight(loads: list[dict]) -> float:
    return sum(float(l.get("weight_tonnes") or 0.0) for l in loads)


def _first_last_dates(loads: list[dict]) -> tuple[str, str]:
    dates = sorted(str(l.get("pickup_date") or "") for l in loads if l.get("pickup_date"))
    return (dates[0], dates[-1]) if dates else ("", "")


def evaluate_ptl(trip: dict, loads: list[dict]) -> dict:
    """Assess whether `loads` can travel together on `trip`."""
    trip_origin = clean_city(trip.get("origin_city") or "")
    trip_dest = clean_city(trip.get("destination_city") or "")
    capacity = trip.get("capacity_tonnes")
    base = {"is_demo": True, "note": "demo feasibility assessment — not a guarantee"}

    if not loads:
        return {**base, "feasible": False, "reason": "no loads provided"}
    if capacity is None or capacity <= 0:
        return {**base, "feasible": False, "reason": "vehicle capacity unknown — cannot assess"}

    total = _total_weight(loads)
    if total > capacity * UTILIZATION_MARGIN:
        return {
            **base,
            "feasible": False,
            "reason": (f"combined weight {total:g}t exceeds usable capacity "
                       f"{capacity * UTILIZATION_MARGIN:g}t (95% of {capacity:g}t)"),
            "total_weight_tonnes": total,
        }

    if not _coherent_route(loads):
        return {
            **base,
            "feasible": False,
            "reason": "loads do not share a single origin/destination corridor",
        }

    # Route overlap with the vehicle's own corridor (demo simplification).
    if trip_origin and trip_dest:
        for l in loads:
            lo = clean_city(l.get("origin_city") or "")
            ld = clean_city(l.get("destination_city") or "")
            # a load must at least start where the trip starts or end where it ends
            if not (lo == trip_origin or ld == trip_dest):
                return {
                    **base,
                    "feasible": False,
                    "reason": f"load {l.get('id')} is not on the vehicle's corridor",
                }

    # Distance estimate for the combined corridor (single corridor).
    first_origin = clean_city(loads[0].get("origin_city") or "")
    last_dest = clean_city(loads[-1].get("destination_city") or "")
    km = CORRIDOR_KM.get((first_origin, last_dest))
    detour_km = round(km * DETOUR_MULTIPLIER) if km else None

    return {
        "feasible": True,
        "total_weight_tonnes": total,
        "capacity_tonnes": capacity,
        "utilization": round(total / capacity, 3),
        "route": f"{first_origin} → {last_dest}",
        "distance_estimate_km": km,
        "detour_multiplier": DETOUR_MULTIPLIER,
        "detour_estimate_km": detour_km,
        "cargo_restrictions": "not assessed (demo schema has no cargo restrictions)",
        "alignment": {
            "first_pickup": _first_last_dates(loads)[0],
            "last_delivery": _first_last_dates(loads)[1],
        },
        "is_demo": True,
        "note": "demo feasibility assessment — not a guarantee",
    }
