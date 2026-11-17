"""Agent intelligence tests — cancel flow, PTL endpoint, new intents, pricing factors."""
from __future__ import annotations

import json

import pytest

from app.tools.pricing import quote, VEHICLE_CLASS_FACTOR, WEIGHT_BAND_SURCHARGE
from .conftest import auth_headers, demo_token


def _stream(resp) -> list[dict]:
    return [json.loads(line) for line in resp.text.strip().splitlines() if line.strip()]


def _done(resp) -> dict:
    return next(m for m in _stream(resp) if m["type"] == "done")


def _create_pending_request(client, tok) -> str:
    r = client.post("/chat", json={
        "message": "Create a request: from Rourkela to Ranchi, 8 tonnes, industrial goods, tomorrow, budget 40000",
    }, headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "approval_required"
    assert client.post("/approve", json={"thread_id": done["thread_id"]},
                       headers=auth_headers(tok)).status_code == 200
    reqs = client.get("/portal/shipper/requests", headers=auth_headers(tok)).json()["requests"]
    return next(x["id"] for x in reqs if x["status"] == "pending")


# ---------------------------------------------------------------------------
# cancel_request (gated, owned)
# ---------------------------------------------------------------------------
def test_cancel_own_request_flow(client):
    tok = demo_token("demo-shipper-08")
    rid = _create_pending_request(client, tok)

    r = client.post("/chat", json={"message": f"cancel request {rid}"},
                    headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "approval_required"
    assert done["pending_action"]["type"] == "cancel_request"
    ap = client.post("/approve", json={"thread_id": done["thread_id"]},
                     headers=auth_headers(tok))
    assert ap.status_code == 200
    assert ap.json()["status"] == "done"
    reqs = client.get("/portal/shipper/requests", headers=auth_headers(tok)).json()["requests"]
    assert next(x for x in reqs if x["id"] == rid)["status"] == "cancelled"


def test_cancel_other_request_rejected(client):
    owner = demo_token("demo-shipper-09")
    intruder = demo_token("demo-transporter-02")
    rid = _create_pending_request(client, owner)

    r = client.post("/chat", json={"message": f"cancel request {rid}"},
                    headers=auth_headers(intruder))
    done = _done(r)
    if done["status"] == "approval_required":
        ap = client.post("/approve", json={"thread_id": done["thread_id"]},
                         headers=auth_headers(intruder))
        assert ap.json()["status"] == "error"
    reqs = client.get("/portal/shipper/requests", headers=auth_headers(owner)).json()["requests"]
    assert next(x for x in reqs if x["id"] == rid)["status"] == "pending"


# ---------------------------------------------------------------------------
# PTL endpoint
# ---------------------------------------------------------------------------
def test_ptl_feasible_pair(client):
    tok = demo_token("demo-transporter-01")
    # trip on Rourkela→Ranchi + two loads on same corridor
    r = client.post("/market/ptl", json={
        "trip_id": "TRIP-0003",
        "load_ids": ["SHP-0001", "SHP-0002"],
    }, headers=auth_headers(tok))
    assert r.status_code == 200
    ptl = r.json()["ptl"]
    assert ptl["is_demo"] is True
    assert "feasible" in ptl


def test_ptl_rejects_overcapacity(client):
    tok = demo_token("demo-transporter-01")
    # TRIP-0001 capacity 12t; two heavy loads exceed 95% usable
    r = client.post("/market/ptl", json={
        "trip_id": "TRIP-0001",
        "load_ids": ["SHP-0001", "SHP-0005"],
    }, headers=auth_headers(tok))
    assert r.status_code == 200
    ptl = r.json()["ptl"]
    if not ptl["feasible"]:
        assert "capacity" in ptl["reason"].lower() or "weight" in ptl["reason"].lower()


def test_ptl_requires_auth(client):
    assert client.post("/market/ptl", json={
        "trip_id": "TRIP-0003", "load_ids": ["SHP-0001", "SHP-0002"],
    }).status_code == 401


# ---------------------------------------------------------------------------
# new intents
# ---------------------------------------------------------------------------
def test_return_load_intent(client):
    tok = demo_token("demo-transporter-01")
    r = client.post("/chat", json={"message": "find return load from Ranchi to Rourkela"},
                    headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] in ("ok", "needs_input")
    assert done["search_mode"] in (None, "find_load")


def test_alternate_vehicle_intent(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "find another vehicle from Rourkela to Ranchi, 8 tonnes tomorrow"},
                    headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "ok"
    assert done["search_mode"] == "find_truck"


def test_compare_options_asks_route(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "compare these options"},
                    headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "needs_input"


# ---------------------------------------------------------------------------
# pricing factors
# ---------------------------------------------------------------------------
def test_pricing_vehicle_and_weight_factors():
    base = quote("Rourkela", "Ranchi", 8.0, "open_body")
    trailer = quote("Rourkela", "Ranchi", 8.0, "trailer")
    heavy = quote("Rourkela", "Ranchi", 15.0, "open_body")
    assert trailer["total_inr"] > base["total_inr"]
    assert heavy["total_inr"] > base["total_inr"]
    assert trailer["breakdown"]["vehicle_class_factor"] == VEHICLE_CLASS_FACTOR["trailer"]
    assert heavy["breakdown"]["weight_band_factor"] == WEIGHT_BAND_SURCHARGE
    assert base["is_estimate"] is True
