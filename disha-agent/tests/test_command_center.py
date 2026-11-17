"""Command Center foundation — new read-only endpoints tests.

GET /market/stats   — global counts + caller-scoped pending requests
GET /market/trips   — active vehicle availability list
GET /approvals      — owner-scoped pending human approvals
"""
from __future__ import annotations

import json

from .conftest import auth_headers, demo_token


def _stream(resp) -> list[dict]:
    return [json.loads(line) for line in resp.text.strip().splitlines() if line.strip()]


def _create_pending(client, tok) -> str:
    r = client.post("/chat", json={
        "message": "Create a request: from Rourkela to Ranchi, 8 tonnes, industrial goods, tomorrow, budget 40000",
    }, headers=auth_headers(tok))
    done = next(m for m in _stream(r) if m["type"] == "done")
    assert done["status"] == "approval_required"
    return done["thread_id"]


def test_market_stats_requires_auth(client):
    assert client.get("/market/stats").status_code == 401


def test_market_stats_shape(client):
    tok = demo_token("demo-shipper-01")
    r = client.get("/market/stats", headers=auth_headers(tok))
    assert r.status_code == 200
    body = r.json()
    assert body["is_demo"] is True
    assert body["source"] == "synthetic_seed_data"
    assert "active_trips" in body and "pending_shipments" in body
    assert "my_pending_requests" in body
    assert isinstance(body["my_pending_requests"], int)


def test_market_trips_lists_active_only(client):
    tok = demo_token("demo-shipper-01")
    r = client.get("/market/trips", headers=auth_headers(tok))
    assert r.status_code == 200
    body = r.json()
    assert body["is_demo"] is True
    assert body["trips"]
    for t in body["trips"]:
        assert t["status"] == "active"
        assert t["is_demo"] is True


def test_approvals_empty_initially(client):
    tok = demo_token("demo-transporter-02")
    r = client.get("/approvals", headers=auth_headers(tok))
    assert r.status_code == 200
    assert r.json()["approvals"] == []


def test_approvals_lists_owner_pending_only(client):
    owner = demo_token("demo-shipper-01")
    other = demo_token("demo-shipper-02")
    tid = _create_pending(client, owner)

    # other user does not see it
    r_other = client.get("/approvals", headers=auth_headers(other))
    assert r_other.status_code == 200
    assert all(a["thread_id"] != tid for a in r_other.json()["approvals"])

    # owner sees exactly the pending action
    r_owner = client.get("/approvals", headers=auth_headers(owner))
    assert r_owner.status_code == 200
    approvals = r_owner.json()["approvals"]
    entry = next(a for a in approvals if a["thread_id"] == tid)
    assert entry["type"] == "create_shipment_request"
    assert "Rourkela" in entry["summary"] or "rourkela" in entry["summary"].lower()

    # approving clears it from the approvals list
    ap = client.post("/approve", json={"thread_id": tid}, headers=auth_headers(owner))
    assert ap.status_code == 200
    r_after = client.get("/approvals", headers=auth_headers(owner))
    assert all(a["thread_id"] != tid for a in r_after.json()["approvals"])
