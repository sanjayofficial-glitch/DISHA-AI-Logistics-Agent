"""Functional Readiness — executable specifications (PHASE 1).

These tests encode the target behavior for the Phase 2 features (J2, J5,
J6, J8). Several are intentionally failing today: they document the gap
and will pass once the corresponding features are implemented. None of
them weaken existing tests or change existing expected behavior.

Spec coverage:
  - J2: transporter vehicle-availability intent recognition; hyphenated
          capacity parsing ("14-tonne").
  - J5: deterministic freight price suggestion with calculation breakdown;
         numeric-only price extraction ("at 38000").
  - J6: negotiation / counter-offer intent (explicit, never silent).
  - J8: honest tracking-unavailable response; human-readable status
         explanations.
"""
from __future__ import annotations

import json

from app.providers.demo import _extract_budget, _extract_weight
from .conftest import auth_headers, demo_token


def _stream(resp) -> list[dict]:
    return [json.loads(line) for line in resp.text.strip().splitlines() if line.strip()]


def _done(resp) -> dict:
    return next(m for m in _stream(resp) if m["type"] == "done")


def _reply(resp) -> str:
    return "".join(m.get("text", "") for m in _stream(resp) if m["type"] == "chunk")


# ---------------------------------------------------------------------------
# J2 — transporter intent + hyphenated capacity
# ---------------------------------------------------------------------------
def test_transporter_availability_intent_not_misread_as_shipper(client):
    """'I have a 14-tonne vehicle available…' must be recognized as a
    transporter availability statement, not a shipper truck-search, and the
    agent must ask for confirmation before publishing availability."""
    tok = demo_token("demo-transporter-01")
    r = client.post("/chat", json={
        "message": "I have a 14-tonne vehicle available from Rourkela to Ranchi.",
    }, headers=auth_headers(tok))
    assert r.status_code == 200
    done = _done(r)
    # Never a shipper-style candidate list…
    assert done["candidates"] == []
    # …and the response asks to confirm the availability (not a search clarification).
    assert done["status"] == "needs_input"
    reply = _reply(r).lower()
    assert "confirm" in reply
    assert "vehicle" in reply


def test_hyphenated_capacity_parsing():
    """'14-tonne' (hyphen, no space) must parse to 14.0 tonnes."""
    assert _extract_weight("i have a 14-tonne vehicle available") == 14.0


# ---------------------------------------------------------------------------
# J5 — freight price suggestion + numeric price extraction
# ---------------------------------------------------------------------------
def test_price_suggestion_returns_quote_with_breakdown(client):
    """Asking 'how much should I pay' must yield a suggested total, a per-
    tonne rate, and a calculation breakdown — never a silent clarification."""
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={
        "message": "How much should I pay for an 8 tonne load from Rourkela to Ranchi?",
    }, headers=auth_headers(tok))
    assert r.status_code == 200
    done = _done(r)
    assert done["status"] == "ok"
    reply = _reply(r).lower()
    assert "₹" in reply or "rs" in reply
    assert "tonne" in reply
    assert "breakdown" in reply or "per tonne" in reply


def test_numeric_only_price_extraction():
    """'send offer for REQ-XYZ at 38000' (currency-prefix-less) => 38000.0."""
    assert _extract_budget("send offer for REQ-ABCD at 38000") == 38000.0


# ---------------------------------------------------------------------------
# J6 — negotiation / counter-offer
# ---------------------------------------------------------------------------
def test_negotiation_probe_gets_explicit_response(client):
    """A counter-offer request must get an explicit negotiation response —
    never a silent misparse into a location clarification."""
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={
        "message": "Can you lower your offer price to 34000?",
    }, headers=auth_headers(tok))
    assert r.status_code == 200
    reply = _reply(r).lower()
    # Must not be the generic search clarification…
    assert "loading kahan" not in reply
    # …and must explicitly address negotiation / counter-offer (or honestly
    # state that negotiation is unsupported).
    assert "nego" in reply or "counter" in reply


# ---------------------------------------------------------------------------
# J8 — status / tracking
# ---------------------------------------------------------------------------
def test_track_returns_honest_unavailable(client):
    """Tracking must never be invented: honest 'not available' in demo mode."""
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={
        "message": "track TRIP-0001",
    }, headers=auth_headers(tok))
    assert r.status_code == 200
    done = _done(r)
    assert done["status"] == "ok"
    reply = _reply(r).lower()
    assert "not available" in reply
    assert "demo" in reply


def test_shipment_status_explained(client):
    """Portal request rows must carry a human-readable status explanation."""
    tok = demo_token("demo-shipper-01")
    r = client.get("/portal/shipper/requests", headers=auth_headers(tok))
    assert r.status_code == 200
    reqs = r.json()["requests"]
    assert reqs
    for row in reqs:
        assert row.get("status_explained"), f"missing status_explained for {row['id']}"
        assert isinstance(row["status_explained"], str)
        assert row["status_explained"].strip()
