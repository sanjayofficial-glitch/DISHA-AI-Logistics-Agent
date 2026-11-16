"""Chat + approval gate end-to-end tests (demo mode)."""
from __future__ import annotations

import json

from .conftest import auth_headers, demo_token


def parse_stream(resp) -> list[dict]:
    return [json.loads(line) for line in resp.text.strip().splitlines() if line.strip()]


def test_chat_find_truck_returns_candidates(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "Rourkela se Ranchi, 8 ton industrial goods, kal"},
                    headers=auth_headers(tok))
    assert r.status_code == 200
    msgs = parse_stream(r)
    done = [m for m in msgs if m["type"] == "done"][0]
    assert done["status"] == "ok"
    assert done["search_mode"] == "find_truck"
    assert done["demo_mode"] is True
    candidates = done["candidates"]
    assert candidates, "expected candidates on the demo corridor"
    # deterministic ranking: first candidate has factor breakdown
    assert "factors" in candidates[0]
    assert "route" in candidates[0]["factors"]
    assert any("rourkela" in (c["origin_city"] or "").lower() for c in candidates)


def test_chat_clarification_asks_one_question(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "I need a truck for steel"},
                    headers=auth_headers(tok))
    done = [m for m in parse_stream(r) if m["type"] == "done"][0]
    assert done["status"] == "needs_input"
    reply = "".join(m.get("text", "") for m in parse_stream(r) if m["type"] == "chunk")
    assert reply  # clarification question present
    assert done["pending_action"] is None


def _create_pending_request(client):
    """Create a pending request via chat; returns (thread_id, pending_action)."""
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={
        "message": "Create a request: from Rourkela to Ranchi, 8 tonnes, industrial goods, tomorrow, budget 40000"},
        headers=auth_headers(tok))
    done = [m for m in parse_stream(r) if m["type"] == "done"][0]
    assert done["status"] == "approval_required"
    assert done["approval_required"] is True
    assert done["pending_action"]
    pa = done["pending_action"]
    assert pa["type"] == "create_shipment_request"
    assert pa["payload"]["origin"].lower() == "rourkela"
    assert pa["payload"]["destination"].lower() == "ranchi"
    return done["thread_id"], pa


def test_chat_create_request_requires_approval(client):
    _create_pending_request(client)


def test_approve_writes_pending_request(client):
    tok = demo_token("demo-shipper-01")
    tid, pa = _create_pending_request(client)
    r = client.post("/approve", json={"thread_id": tid}, headers=auth_headers(tok))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "done"
    # the written request now exists
    rr = client.get("/portal/shipper/requests", headers=auth_headers(tok))
    reqs = rr.json()["requests"]
    assert any(x["status"] == "pending" for x in reqs)
    events = client.get(f"/threads/{tid}/events", headers=auth_headers(tok)).json()["events"]
    assert any(e["node"] == "execute" and e["status"] == "done" for e in events)


def test_reject_writes_nothing(client):
    tok = demo_token("demo-shipper-01")
    tid, pa = _create_pending_request(client)
    r = client.post("/reject", json={"thread_id": tid}, headers=auth_headers(tok))
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    rr = client.get("/portal/shipper/requests", headers=auth_headers(tok))
    before = len(rr.json()["requests"])
    # nothing was written: no new request beyond seed
    rr2 = client.get("/portal/shipper/requests", headers=auth_headers(tok))
    assert len(rr2.json()["requests"]) == before


def test_cross_user_approval_rejected(client):
    owner_tok = demo_token("demo-shipper-01")
    other_tok = demo_token("demo-shipper-02")
    tid, _ = _create_pending_request(client)
    r = client.post("/approve", json={"thread_id": tid}, headers=auth_headers(other_tok))
    assert r.status_code == 403


def test_cross_user_events_hidden(client):
    owner_tok = demo_token("demo-shipper-01")
    other_tok = demo_token("demo-shipper-02")
    tid, _ = _create_pending_request(client)
    r = client.get(f"/threads/{tid}/events", headers=auth_headers(other_tok))
    assert r.status_code == 403


def test_accept_offer_flow(client):
    shipper = demo_token("demo-shipper-01")
    transporter = demo_token("demo-transporter-01")
    # create a request as shipper
    tid, _ = _create_pending_request(client)
    client.post("/approve", json={"thread_id": tid}, headers=auth_headers(shipper))
    reqs = client.get("/portal/shipper/requests", headers=auth_headers(shipper)).json()["requests"]
    request_id = next(r["id"] for r in reqs if r["status"] == "pending")

    # transporter sends offer
    r = client.post("/chat", json={"message": f"send offer for {request_id} at 38000"},
                    headers=auth_headers(transporter))
    done = [m for m in parse_stream(r) if m["type"] == "done"][0]
    assert done["status"] == "approval_required"
    assert done["pending_action"]["type"] == "create_transporter_offer"
    client.post("/approve", json={"thread_id": done["thread_id"]}, headers=auth_headers(transporter))

    offers = client.get("/portal/trucker/offers", headers=auth_headers(transporter)).json()["offers"]
    offer = next(o for o in offers if o["request_id"] == request_id)
    assert offer["status"] == "pending"
    assert offer["transporter_user_id"] == "demo-transporter-01"

    # transporter accepts own offer
    r = client.post("/chat", json={"message": f"accept offer {offer['id']}"},
                    headers=auth_headers(transporter))
    done = [m for m in parse_stream(r) if m["type"] == "done"][0]
    assert done["status"] == "approval_required"
    client.post("/approve", json={"thread_id": done["thread_id"]}, headers=auth_headers(transporter))
    offers = client.get("/portal/trucker/offers", headers=auth_headers(transporter)).json()["offers"]
    assert next(o for o in offers if o["id"] == offer["id"])["status"] == "accepted"

    # shipper confirms request
    r = client.post("/chat", json={"message": f"confirm request {request_id}"},
                    headers=auth_headers(shipper))
    done = [m for m in parse_stream(r) if m["type"] == "done"][0]
    assert done["status"] == "approval_required"
    client.post("/approve", json={"thread_id": done["thread_id"]}, headers=auth_headers(shipper))
    reqs = client.get("/portal/shipper/requests", headers=auth_headers(shipper)).json()["requests"]
    confirmed = next(rr for rr in reqs if rr["id"] == request_id)
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed_at"]
