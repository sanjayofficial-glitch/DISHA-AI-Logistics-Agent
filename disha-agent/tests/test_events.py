"""Events + metrics tests."""
from .conftest import auth_headers, demo_token
from .test_chat import test_chat_find_truck_returns_candidates


def test_events_recorded_per_node(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={
        "message": "Create a request: from Rourkela to Ranchi, 8 tonnes, tomorrow"},
        headers=auth_headers(tok))
    import json as _json
    lines = [_json.loads(x) for x in r.text.strip().splitlines() if x.strip()]
    done = [m for m in lines if m["type"] == "done"][0]
    events = client.get(f"/threads/{done['thread_id']}/events", headers=auth_headers(tok)).json()["events"]
    nodes = [e["node"] for e in events]
    assert "understand" in nodes
    assert "coordinate" in nodes
    assert "execute" not in nodes  # not approved yet


def test_events_owner_only(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "Rourkela se Ranchi, 8 ton, kal"},
                    headers=auth_headers(tok))
    import json as _json
    lines = [_json.loads(x) for x in r.text.strip().splitlines() if x.strip()]
    done = [m for m in lines if m["type"] == "done"][0]
    other = demo_token("demo-shipper-02")
    rr = client.get(f"/threads/{done['thread_id']}/events", headers=auth_headers(other))
    assert rr.status_code == 403


def test_metrics_endpoint(client):
    tok = demo_token("demo-shipper-01")
    r = client.get("/metrics", headers=auth_headers(tok))
    assert r.status_code == 200
    body = r.json()
    assert body["is_demo"] is True
    for key in ("offers_sent", "acceptance_rate", "match_success_rate"):
        assert key in body
