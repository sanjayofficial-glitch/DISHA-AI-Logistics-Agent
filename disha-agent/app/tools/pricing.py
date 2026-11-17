"""Deterministic freight pricing engine — ESTIMATES ONLY.

Every number here is a documented demo assumption, never a verified market
quotation. The engine only knows the synthetic demo corridor set; unknown
routes return an honest "unavailable" answer instead of an invented
distance. Pricing never writes anything — it is pure read-only math.
"""
from __future__ import annotations

from .marketplace import clean_city

# ---------------------------------------------------------------------------
# Documented assumption constants (demo only)
# ---------------------------------------------------------------------------
# Synthetic distances (km) for the demo corridor set. These are demo figures
# used only for the competition narrative — not real routing distances.
DEMO_CORRIDOR_KM: dict[tuple[str, str], int] = {
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

# Base operating cost per km (₹) for a 12–16-tonne truck class: driver wage,
# vehicle depreciation, insurance and maintenance prorated per km.
BASE_CHARGE_PER_KM_INR = 28.0

# Multiplier covering fuel + tolls + route overhead on top of base cost.
FUEL_TOLL_FACTOR = 1.35

# Vehicle-class factor (relative to a baseline open-body truck).
VEHICLE_CLASS_FACTOR: dict[str, float] = {
    "open_body": 1.00,
    "covered_body": 1.03,
    "trailer": 1.08,
}

# Weight-band surcharge (applied above 12 t) — heavier loads cost more to haul.
WEIGHT_BAND_THRESHOLD_T = 12.0
WEIGHT_BAND_SURCHARGE = 1.05

# Estimates are rounded to this step (₹) for readability.
ROUNDING_STEP_INR = 10.0

ASSUMPTIONS = [
    "Demo corridor distance table (synthetic, not real routing)",
    f"Operating cost base ₹{BASE_CHARGE_PER_KM_INR:g}/km (12–16t truck class)",
    f"Fuel + toll + route overhead factor {FUEL_TOLL_FACTOR}",
    "Vehicle-class factor applied (open body 1.00, covered 1.03, trailer 1.08)",
    f"Weight-band surcharge {WEIGHT_BAND_SURCHARGE} above {WEIGHT_BAND_THRESHOLD_T:g}t",
    "Single-leg full truckload; no multi-stop or loading/unloading charges",
    "Estimate only — not a verified market quotation",
]


def quote(origin: str, destination: str, weight_tonnes: float,
          vehicle_type: str | None = None) -> dict:
    """Return a deterministic freight estimate for a demo corridor.

    Returns ``{"available": False, "reason": ...}`` for unknown routes —
    never an invented distance.
    """
    o, d = clean_city(origin), clean_city(destination)
    if not o or not d:
        return {"available": False, "reason": "origin and destination are required."}
    if not weight_tonnes or weight_tonnes <= 0:
        return {"available": False, "reason": "weight_tonnes must be > 0."}

    km = DEMO_CORRIDOR_KM.get((o, d))
    if km is None:
        return {
            "available": False,
            "reason": (f"No distance data for {o} → {d} in the demo corridor set. "
                       "Cannot estimate — I won't invent a distance."),
        }

    total_raw = (
        BASE_CHARGE_PER_KM_INR
        * km
        * FUEL_TOLL_FACTOR
        * VEHICLE_CLASS_FACTOR.get((vehicle_type or "open_body").strip().lower(), 1.00)
        * (WEIGHT_BAND_SURCHARGE if weight_tonnes > WEIGHT_BAND_THRESHOLD_T else 1.0)
    )
    total = round(total_raw / ROUNDING_STEP_INR) * ROUNDING_STEP_INR
    per_tonne = round(total / weight_tonnes, 0)

    vehicle_factor = VEHICLE_CLASS_FACTOR.get((vehicle_type or "open_body").strip().lower(), 1.00)
    weight_factor = WEIGHT_BAND_SURCHARGE if weight_tonnes > WEIGHT_BAND_THRESHOLD_T else 1.0

    return {
        "available": True,
        "origin": o,
        "destination": d,
        "distance_assumption_km": km,
        "weight_tonnes": weight_tonnes,
        "vehicle_type": vehicle_type or "unknown",
        "total_inr": total,
        "per_tonne_inr": per_tonne,
        "breakdown": {
            "distance_assumption_km": km,
            "base_charge_per_km_inr": BASE_CHARGE_PER_KM_INR,
            "fuel_toll_factor": FUEL_TOLL_FACTOR,
            "vehicle_class_factor": vehicle_factor,
            "weight_band_factor": weight_factor,
            "formula": (f"₹{BASE_CHARGE_PER_KM_INR:g}/km × {km} km × "
                        f"{FUEL_TOLL_FACTOR} × vehicle {vehicle_factor} × "
                        f"weight {weight_factor} ≈ ₹{total:,.0f}"),
        },
        "assumptions": list(ASSUMPTIONS),
        "is_estimate": True,
    }
