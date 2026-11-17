"""Multilingual intent tests — Hindi/Hinglish/Odia phrases."""
from __future__ import annotations

import json

from .conftest import auth_headers, demo_token


def _done(resp) -> dict:
    return next(m for m in (json.loads(x) for x in resp.text.strip().splitlines() if x.strip()) if m["type"] == "done")


def _reply(resp) -> str:
    return "".join(
        m.get("text", "") for m in
        (json.loads(x) for x in resp.text.strip().splitlines() if x.strip())
        if m["type"] == "chunk"
    )


def test_hinglish_find_truck(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "mujhe Rourkela se Ranchi 8 ton truck chahiye kal"},
                    headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "ok"
    assert done["search_mode"] == "find_truck"


def test_odia_create_request(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "request karantu Rourkela se Ranchi, 8 tonnes, kal"},
                    headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "approval_required"
    assert done["pending_action"]["type"] == "create_shipment_request"


def test_odia_cancel(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "bata karantu REQ-HIST3"},
                    headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "approval_required"
    assert done["pending_action"]["type"] == "cancel_request"


def test_odia_remember(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "monarakhiba prefer open body trucks"},
                    headers=auth_headers(tok))
    done = _done(r)
    assert done["status"] == "ok"
    assert "remember" in _reply(r).lower()
