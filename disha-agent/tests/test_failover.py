"""Honesty/failover tests.

When a real provider IS configured and fails, the service must surface a
clean error — never a fake reply. In demo mode no provider key exists, so we
simulate a configured-but-failing provider by patching.
"""
from __future__ import annotations

from unittest.mock import patch

from .conftest import auth_headers, demo_token


class FailingProvider:
    name = "failing"

    def complete(self, system: str, user: str) -> str:
        raise RuntimeError("boom")


def test_provider_failure_is_honest(client):
    tok = demo_token("demo-shipper-01")
    with patch("app.nodes.get_provider", return_value=FailingProvider()):
        r = client.post("/chat", json={"message": "Rourkela se Ranchi, 8 ton, kal"},
                        headers=auth_headers(tok))
    assert r.status_code == 200
    import json as _json
    msgs = [_json.loads(x) for x in r.text.strip().splitlines() if x.strip()]
    done = [m for m in msgs if m["type"] == "done"][0]
    assert done["status"] == "error"
    reply = "".join(m.get("text", "") for m in msgs if m["type"] == "chunk")
    assert "unavailable" in reply.lower() or "boom" in reply.lower()
    # no fake candidates
    assert done["candidates"] == []


def test_demo_mode_labeled(client):
    tok = demo_token("demo-shipper-01")
    r = client.post("/chat", json={"message": "help"}, headers=auth_headers(tok))
    assert r.status_code == 200
    import json as _json
    msgs = [_json.loads(x) for x in r.text.strip().splitlines() if x.strip()]
    done = [m for m in msgs if m["type"] == "done"][0]
    assert done["provider"] == "demo"
    assert done["demo_mode"] is True
