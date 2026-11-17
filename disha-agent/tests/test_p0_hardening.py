"""P0 hardening tests.

P0-1: resource ownership on accept_offer / confirm_request.
P0-2: explicit store selector (DISHA_STORE).
P0-3: confirm-request requires an accepted offer.
P0-5: approval expiry.
"""
from __future__ import annotations

import json

import pytest

from app.config import settings
from app.database import SQLiteStore, SupabaseStore, get_store
from .conftest import auth_headers, demo_token


def _stream(resp) -> list[dict]:
    return [json.loads(line) for line in resp.text.strip().splitlines() if line.strip()]


def _done(resp) -> dict:
    return next(m for m in _stream(resp) if m["type"] == "done")


def _create_pending_request(client, tok) -> tuple[str, str]:
    """Create a request via chat and approve it; returns (thread, request_id)."""
    r = client.post("/chat", json={
        "message": "Create a request: from Rourkela to Ranchi, 8 tonnes, industrial goods, tomorrow, budget 40000",
    }, headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "approval_required"
    assert client.post("/approve", json={"thread_id": done["thread_id"]},
                       headers=auth_headers(tok)).status_code == 200
    reqs = client.get("/portal/shipper/requests", headers=auth_headers(tok)).json()["requests"]
    rid = next(x["id"] for x in reqs if x["status"] == "pending")
    return done["thread_id"], rid


def _send_offer(client, tok, request_id) -> str:
    r = client.post("/chat", json={"message": f"send offer for {request_id} at 38000"},
                    headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "approval_required"
    assert client.post("/approve", json={"thread_id": done["thread_id"]},
                       headers=auth_headers(tok)).status_code == 200
    offers = client.get("/portal/trucker/offers", headers=auth_headers(tok)).json()["offers"]
    return next(o["id"] for o in offers if o["request_id"] == request_id)


def _chat_approve(client, tok, message) -> dict:
    r = client.post("/chat", json={"message": message}, headers=auth_headers(tok))
    done = _done(r)
    if done["status"] == "approval_required":
        ap = client.post("/approve", json={"thread_id": done["thread_id"]},
                         headers=auth_headers(tok))
        return ap.json()
    return done


# ---------------------------------------------------------------------------
# P0-1: ownership
# ---------------------------------------------------------------------------
def test_cross_user_accept_offer_rejected(client):
    shipper = demo_token("demo-shipper-01")
    transporter = demo_token("demo-transporter-01")
    intruder = demo_token("demo-shipper-02")
    _, rid = _create_pending_request(client, shipper)
    offer_id = _send_offer(client, transporter, rid)

    res = _chat_approve(client, intruder, f"accept offer {offer_id}")
    assert res.get("status") == "error"
    offers = client.get("/portal/trucker/offers", headers=auth_headers(transporter)).json()["offers"]
    assert next(o for o in offers if o["id"] == offer_id)["status"] == "pending"


def test_cross_user_confirm_request_rejected(client):
    shipper = demo_token("demo-shipper-04")
    intruder = demo_token("demo-transporter-02")
    _, rid = _create_pending_request(client, shipper)

    res = _chat_approve(client, intruder, f"confirm request {rid}")
    assert res.get("status") == "error"
    reqs = client.get("/portal/shipper/requests", headers=auth_headers(shipper)).json()["requests"]
    assert next(r for r in reqs if r["id"] == rid)["status"] == "pending"


# ---------------------------------------------------------------------------
# P0-3: confirm requires accepted offer
# ---------------------------------------------------------------------------
def test_confirm_without_accepted_offer_rejected(client):
    shipper = demo_token("demo-shipper-05")
    _, rid = _create_pending_request(client, shipper)

    res = _chat_approve(client, shipper, f"confirm request {rid}")
    assert res.get("status") == "error"
    reqs = client.get("/portal/shipper/requests", headers=auth_headers(shipper)).json()["requests"]
    assert next(r for r in reqs if r["id"] == rid)["status"] == "pending"


def test_confirm_after_accepted_offer_succeeds(client):
    shipper = demo_token("demo-shipper-06")
    transporter = demo_token("demo-transporter-02")
    _, rid = _create_pending_request(client, shipper)
    _send_offer(client, transporter, rid)
    # transporter accepts own offer
    offers = client.get("/portal/trucker/offers", headers=auth_headers(transporter)).json()["offers"]
    offer_id = next(o["id"] for o in offers if o["request_id"] == rid)
    assert _chat_approve(client, transporter, f"accept offer {offer_id}")["status"] == "done"

    res = _chat_approve(client, shipper, f"confirm request {rid}")
    assert res.get("status") == "done"
    reqs = client.get("/portal/shipper/requests", headers=auth_headers(shipper)).json()["requests"]
    confirmed = next(r for r in reqs if r["id"] == rid)
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed_at"]


# ---------------------------------------------------------------------------
# P0-2: explicit store selector
# ---------------------------------------------------------------------------
def test_store_default_demo_even_with_supabase_env(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://x.supabase.co")
    monkeypatch.setattr(settings, "supabase_anon_key", "k")
    monkeypatch.setattr(settings, "store", "demo")
    assert isinstance(get_store("any-token"), SQLiteStore)


def test_store_supabase_requires_credentials(monkeypatch):
    monkeypatch.setattr(settings, "store", "supabase")
    monkeypatch.setattr(settings, "supabase_url", None)
    monkeypatch.setattr(settings, "supabase_anon_key", None)
    with pytest.raises(ValueError):
        get_store("tok")


def test_store_supabase_requires_user_token(monkeypatch):
    monkeypatch.setattr(settings, "store", "supabase")
    monkeypatch.setattr(settings, "supabase_url", "https://x.supabase.co")
    monkeypatch.setattr(settings, "supabase_anon_key", "k")
    with pytest.raises(ValueError):
        get_store()


def test_store_supabase_active_when_requested(monkeypatch):
    monkeypatch.setattr(settings, "store", "supabase")
    monkeypatch.setattr(settings, "supabase_url", "https://x.supabase.co")
    monkeypatch.setattr(settings, "supabase_anon_key", "k")
    assert isinstance(get_store("some-jwt"), SupabaseStore)


# ---------------------------------------------------------------------------
# P0-5: approval expiry
# ---------------------------------------------------------------------------
def test_expired_approval_is_not_written(client):
    from app.service import service

    tok = demo_token("demo-shipper-07")
    # create a pending action but DO NOT approve it yet
    r = client.post("/chat", json={
        "message": "Create a request: from Rourkela to Ranchi, 8 tonnes, industrial goods, tomorrow, budget 40000",
    }, headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "approval_required"
    tid = done["thread_id"]

    # back-date the pending action in checkpoint state
    graph = service._ensure_graph()
    config = {"configurable": {"thread_id": tid}}
    state = graph.get_state(config).values
    pa = dict(state["pending_action"])
    pa["created_at"] = "2020-01-01T00:00:00+00:00"
    graph.update_state(config, {"pending_action": pa})

    before = len(client.get("/portal/shipper/requests", headers=auth_headers(tok)).json()["requests"])
    res = client.post("/approve", json={"thread_id": tid}, headers=auth_headers(tok))
    assert res.status_code == 200
    assert res.json()["status"] == "expired"
    after = len(client.get("/portal/shipper/requests", headers=auth_headers(tok)).json()["requests"])
    assert after == before
