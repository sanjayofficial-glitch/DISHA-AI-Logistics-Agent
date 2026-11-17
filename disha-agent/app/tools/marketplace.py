"""Marketplace tools — read-only search + gated write actions.

All writes are performed ONLY from the `execute` node, which runs behind the
LangGraph approval gate. Values are validated by Pydantic first.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from ..context import current_user_id
from .matching import rank_candidates
from .registry import Tool, register

# Strict city cleaning: keep letters, digits and spaces only. This both
# normalizes and eliminates any SQL/PostgREST injection attempt (quotes,
# semicolons, comment markers etc. are stripped).
_CITY_CLEAN = re.compile(r"[^a-zA-Z0-9 ]")


def clean_city(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = _CITY_CLEAN.sub("", value.strip().lower())
    return re.sub(r"\s+", " ", cleaned).strip()[:100]


# ---------------------------------------------------------------------------
# Read-only tools
# ---------------------------------------------------------------------------
class SearchTripsArgs(BaseModel):
    origin: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=100)


def _search_trips(store, args: dict) -> dict:
    origin, destination = clean_city(args["origin"]), clean_city(args["destination"])
    rows = store.search_trips(origin, destination)
    return {"count": len(rows), "rows": rows}


class SearchShipmentsArgs(BaseModel):
    origin: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=100)


def _search_shipments(store, args: dict) -> dict:
    origin, destination = clean_city(args["origin"]), clean_city(args["destination"])
    rows = store.search_shipments(origin, destination)
    return {"count": len(rows), "rows": rows}


class MarketStatsArgs(BaseModel):
    pass


def _market_stats(store, args: dict) -> dict:
    return store.get_market_stats()


def rank_rows(store, rows: list[dict], intent: dict, mode: str) -> list[dict]:
    return rank_candidates(rows, intent, mode)


# ---------------------------------------------------------------------------
# Write tools (gated — executed only after approval)
# ---------------------------------------------------------------------------
class CreateShipmentRequestArgs(BaseModel):
    origin: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=100)
    goods: str = Field(default="", max_length=200)
    weight_tonnes: float = Field(gt=0, le=1000)
    vehicle_type: str = Field(default="", max_length=50)
    pickup_date: str = Field(default="", max_length=10)
    budget_inr: float | None = Field(default=None, gt=0)


def _create_shipment_request(store, args: dict) -> dict:
    payload = dict(args)
    payload["origin"] = clean_city(args["origin"])
    payload["destination"] = clean_city(args["destination"])
    payload["shipper_user_id"] = current_user_id()
    row = store.create_shipment_request(payload)
    return {"request_id": row["id"], "status": row["status"], "row": row}


class CreateTransporterOfferArgs(BaseModel):
    request_id: str = Field(min_length=4, max_length=32)
    price_inr: float | None = Field(default=None, gt=0)
    trip_id: str | None = Field(default=None, max_length=32)


def _create_transporter_offer(store, args: dict) -> dict:
    payload = {
        "request_id": args["request_id"].strip().upper(),
        "transporter_user_id": current_user_id(),
        "trip_id": (args.get("trip_id") or "").strip().upper() or None,
        "price_inr": args.get("price_inr"),
    }
    row = store.create_transporter_offer(payload)
    return {"offer_id": row["id"], "status": row["status"], "row": row}


class AcceptOfferArgs(BaseModel):
    offer_id: str = Field(min_length=4, max_length=32)


def _accept_offer(store, args: dict) -> dict:
    """Accept an offer — only by the transporter who owns it."""
    offer_id = args["offer_id"].strip().upper()
    offer = store.get_offer(offer_id)
    if not offer:
        raise ValueError("offer not found")
    if offer.get("transporter_user_id") != current_user_id():
        raise ValueError("forbidden: you can only accept your own offers")
    row = store.accept_offer(offer_id)
    return {"offer_id": row["id"], "status": row["status"], "row": row}


class ConfirmRequestArgs(BaseModel):
    request_id: str = Field(min_length=4, max_length=32)


def _confirm_request(store, args: dict) -> dict:
    """Confirm a request — only by the shipper who owns it, and only when
    at least one offer on the request has been accepted."""
    request_id = args["request_id"].strip().upper()
    req = store.get_request(request_id)
    if not req:
        raise ValueError("request not found")
    if req.get("shipper_user_id") != current_user_id():
        raise ValueError("forbidden: you can only confirm your own requests")
    offers = store.get_offers_for_request(request_id)
    if not any(o.get("status") == "accepted" for o in offers):
        raise ValueError("cannot confirm: no accepted offer on this request yet")
    row = store.confirm_request(request_id)
    return {"request_id": row["id"], "status": row["status"], "row": row}


class CancelRequestArgs(BaseModel):
    request_id: str = Field(min_length=4, max_length=32)


def _cancel_request(store, args: dict) -> dict:
    """Cancel a request — only by the shipper who owns it (approval-gated)."""
    request_id = args["request_id"].strip().upper()
    req = store.get_request(request_id)
    if not req:
        raise ValueError("request not found")
    if req.get("shipper_user_id") != current_user_id():
        raise ValueError("forbidden: you can only cancel your own requests")
    row = store.cancel_request(request_id)
    return {"request_id": row["id"], "status": row["status"], "row": row}


class SendNotificationArgs(BaseModel):
    type: str = Field(max_length=50)
    title: str = Field(max_length=200)
    body: str = Field(max_length=2000)


def _send_notification(store, args: dict) -> dict:
    row = store.send_notification(
        current_user_id(), args["type"], args["title"], args["body"]
    )
    return {"notification_id": row["id"]}


class RegisterVehicleAvailabilityArgs(BaseModel):
    origin: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=100)
    capacity_tonnes: float = Field(gt=0, le=200)
    vehicle_type: str = Field(default="open_body", max_length=50)
    pickup_date: str = Field(default="", max_length=10)


def _register_vehicle_availability(store, args: dict) -> dict:
    """Publish a transporter's vehicle availability (approval-gated)."""
    payload = dict(args)
    payload["origin"] = clean_city(args["origin"])
    payload["destination"] = clean_city(args["destination"])
    payload["transporter_user_id"] = current_user_id()
    row = store.register_vehicle_availability(payload)
    return {"trip_id": row["id"], "status": row["status"], "row": row}


class MakeCounterOfferArgs(BaseModel):
    request_id: str = Field(min_length=4, max_length=32)
    amount_inr: float = Field(gt=0, le=1_000_000_000)
    message: str = Field(default="", max_length=500)


def _make_counter_offer(store, args: dict) -> dict:
    """Record a negotiation counter-offer. Participants only (shipper or a
    transporter with an offer on the request). Never auto-accepts anything."""
    rid = args["request_id"].strip().upper()
    req = store.get_request(rid)
    if not req:
        raise ValueError("request not found")
    uid = current_user_id()
    offers = store.get_offers_for_request(rid)
    is_participant = req.get("shipper_user_id") == uid or any(
        o.get("transporter_user_id") == uid for o in offers
    )
    if not is_participant:
        raise ValueError("only participants in this request can negotiate")
    row = store.make_counter_offer({
        "request_id": rid,
        "offer_id": None,
        "party_user_id": uid,
        "amount_inr": args["amount_inr"],
        "message": args["message"],
    })
    return {"negotiation_id": row["id"], "status": row["status"], "row": row}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
MAKERS = [
    ("search_trips", "Search active trips for an origin/destination pair.", SearchTripsArgs, _search_trips, True),
    ("search_shipments", "Search pending shipments for an origin/destination pair.", SearchShipmentsArgs, _search_shipments, True),
    ("get_market_stats", "Counts of active trips and pending shipments visible to the caller.", MarketStatsArgs, _market_stats, True),
    ("create_shipment_request", "Shipper asks for a truck: inserts a PENDING request.", CreateShipmentRequestArgs, _create_shipment_request, False),
    ("create_transporter_offer", "Transporter offers on a shipment: inserts a PENDING offer.", CreateTransporterOfferArgs, _create_transporter_offer, False),
    ("accept_offer", "Transporter accepts a pending offer.", AcceptOfferArgs, _accept_offer, False),
    ("confirm_request", "Shipper confirms a pending request (booking confirmed).", ConfirmRequestArgs, _confirm_request, False),
    ("send_notification", "Insert a notification row.", SendNotificationArgs, _send_notification, False),
    ("register_vehicle_availability", "Transporter publishes vehicle availability (active trip row).", RegisterVehicleAvailabilityArgs, _register_vehicle_availability, False),
    ("make_counter_offer", "Record a negotiation counter-offer on a request (participants only).", MakeCounterOfferArgs, _make_counter_offer, False),
    ("cancel_request", "Shipper cancels their own request (pending or confirmed).", CancelRequestArgs, _cancel_request, False),
]

for _name, _desc, _schema, _handler, _ro in MAKERS:
    register(Tool(_name, _desc, _schema, _handler, read_only=_ro))
