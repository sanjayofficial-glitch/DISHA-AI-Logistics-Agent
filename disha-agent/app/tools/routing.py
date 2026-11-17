"""Routing intelligence — demo corridor table with honest estimates.

Real road routing (OSRM/OSM) can be plugged in later via DISHA_OSRM_URL;
until then we use a documented demo corridor table and never claim real
routing output. Distances are ASSUMPTIONS for the demo only.
"""
from __future__ import annotations

import os

from .marketplace import clean_city

# Demo corridor distances (km) — synthetic, for the competition narrative only.
CORRIDOR_KM: dict[tuple[str, str], int] = {
    ("rourkela", "ranchi"): 320,
    ("rourkela", "kolkata"): 460,
    ("kolkata", "rourkela"): 460,
    ("ranchi", "kolkata"): 330,
    ("kolkata", "siliguri"): 550,
    ("jamshedpur", "ranchi"): 130,
    ("bhubaneswar", "rourkela"): 340,
    ("ranchi", "patna"): 260,
    ("rourkela", "nagpur"): 640,
    ("ranchi", "nagpur"): 450,
}

# Typical detour cost multiplier when an extra stop is added on a leg.
DETOUR_MULTIPLIER = 1.12

OSRM_URL = os.getenv("DISHA_OSRM_URL", "").rstrip("/")


def corridor_distance(origin: str, destination: str) -> int | None:
    """Distance in km, or None when the corridor is unknown."""
    o, d = clean_city(origin), clean_city(destination)
    return CORRIDOR_KM.get((o, d))


def routing_source() -> str:
    return "osrm" if OSRM_URL else "demo_corridor_table"
