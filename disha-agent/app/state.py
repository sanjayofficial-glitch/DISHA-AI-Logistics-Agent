"""Graph state and shared schemas."""
from __future__ import annotations

from typing import TypedDict


class Intent(TypedDict, total=False):
    action: str  # find_truck | find_load | create_request | send_offer |
    #              accept_offer | confirm_request | remember | track | help | chat
    origin: str
    destination: str
    goods: str
    weight_tonnes: float
    vehicle_type: str
    pickup_date: str  # ISO date
    budget_inr: float
    request_id: str
    offer_id: str
    trip_id: str
    fact_text: str
    missing_fields: list[str]
    clarification: str  # question to ask when fields are missing
    summary: str  # human-readable summary of understood intent


class Candidate(TypedDict, total=False):
    id: str
    source_table: str  # trips | shipments | requests
    origin_city: str
    destination_city: str
    total_score: float
    factors: dict
    explanation: str
    extra: dict
    is_demo: bool
    source: str


class PendingAction(TypedDict, total=False):
    type: str  # create_shipment_request | create_transporter_offer | accept_offer | confirm_request
    payload: dict
    summary: str
    created_at: str


class DishaState(TypedDict, total=False):
    thread_id: str
    user_id: str
    message: str
    intent: Intent
    candidates: list[Candidate]
    pending_action: PendingAction
    approval_required: bool
    reply: str
    provider: str
    status: str  # ok | needs_input | approval_required | done | error
    search_mode: str  # find_truck | find_load
    raw_rows: list[dict]
    tool_error: str | None
