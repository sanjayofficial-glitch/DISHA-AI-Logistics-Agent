"""LoadSaathi integration contracts — Pydantic models that define the row
shapes DISHA expects from the Supabase marketplace tables.

These contracts are the single source of truth for the integration adapter.
They are intentionally strict about the fields DISHA relies on; anything the
real schema does not provide should be raised here so we fail loudly instead
of silently mis-reading production data.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TripRow(BaseModel):
    id: str
    transporter_user_id: str
    origin_city: str
    destination_city: str
    departure_date: Optional[str] = None
    capacity_tonnes: Optional[float] = None
    price_per_tonne: Optional[float] = None
    vehicle_type: str = ""
    reliability_score: Optional[float] = 0.5
    status: str = "active"


class ShipmentRow(BaseModel):
    id: str
    shipper_user_id: str
    origin_city: str
    destination_city: str
    pickup_date: Optional[str] = None
    weight_tonnes: Optional[float] = None
    goods: str = ""
    vehicle_type: str = ""
    budget_inr: Optional[float] = None
    status: str = "pending"


class RequestRow(BaseModel):
    id: str
    shipper_user_id: str
    origin_city: str
    destination_city: str
    goods: str = ""
    weight_tonnes: Optional[float] = None
    vehicle_type: str = ""
    pickup_date: Optional[str] = None
    budget_inr: Optional[float] = None
    status: str = "pending"
    created_at: Optional[str] = None
    confirmed_at: Optional[str] = None


class OfferRow(BaseModel):
    id: str
    request_id: str
    transporter_user_id: str
    trip_id: Optional[str] = None
    price_inr: Optional[float] = None
    status: str = "pending"
    created_at: Optional[str] = None
    decided_at: Optional[str] = None


class NotificationRow(BaseModel):
    id: str
    user_id: str
    type: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    read: bool = False
    created_at: Optional[str] = None


ROW_CONTRACTS = {
    "trips": TripRow,
    "shipments": ShipmentRow,
    "requests": RequestRow,
    "shipment_requests": OfferRow,
    "notifications": NotificationRow,
}


def validate_row(table: str, row: dict) -> dict:
    """Validate one row against its contract. Raises on shape mismatch."""
    model = ROW_CONTRACTS.get(table)
    if model is None:
        raise ValueError(f"no contract defined for table {table!r}")
    return model.model_validate(row).model_dump(exclude_none=True)
