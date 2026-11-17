"""Pre-deployment hardening tests.

M1 — provider failover: bounded retry on retryable errors, fallback
     provider, honest error when both fail, no retry on permanent errors.
M2 — strict production authentication: production config must set the
     Clerk->Supabase contract and a real JWT secret (fail closed); negative
     JWT tests (algorithm, issuer, audience, sub).
M3 — demo-login isolation: demo login is blocked whenever Supabase is
     configured or ENVIRONMENT=production.
"""
from __future__ import annotations

import datetime as dt
import json

import jwt
import pytest
from fastapi import HTTPException
from unittest.mock import patch

from app.auth import create_dev_token, verify_token
from app.config import Settings, settings
from app.nodes import _complete_with_retry
from app.providers import ProviderError
from .conftest import auth_headers, demo_token


# ---------------------------------------------------------------------------
# M1 — provider failover helpers
# ---------------------------------------------------------------------------
class FakeProvider:
    """Scripted provider: each `complete` call pops the next outcome."""

    name = "fake"

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        outcome = self.results.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class BadAlwaysProvider:
    name = "gemini"

    def complete(self, system, user):
        raise ProviderError("gemini HTTP 500", retryable=True)


class GoodProvider:
    name = "groq"

    def complete(self, system, user):
        if "Extract a structured intent" in user:
            return '{"action":"chat","summary":"ok"}'
        return "OK"


def test_retry_on_retryable_error_once():
    p = FakeProvider([ProviderError("rate limited", retryable=True), "ok"])
    assert _complete_with_retry(p, "", "") == "ok"
    assert p.calls == 2


def test_no_retry_on_permanent_error():
    p = FakeProvider([ProviderError("bad request", retryable=False)])
    with pytest.raises(ProviderError):
        _complete_with_retry(p, "", "")
    assert p.calls == 1


def test_retry_exhausted_raises():
    p = FakeProvider([
        ProviderError("5xx", retryable=True),
        ProviderError("5xx", retryable=True),
    ])
    with pytest.raises(ProviderError):
        _complete_with_retry(p, "", "")
    assert p.calls == 2


def test_generic_exception_wrapped_as_permanent():
    p = FakeProvider([RuntimeError("boom")])
    with pytest.raises(ProviderError):
        _complete_with_retry(p, "", "")
    assert p.calls == 1


def test_fallback_success(client):
    with patch("app.nodes.get_provider", return_value=BadAlwaysProvider()), \
         patch("app.nodes.get_fallback_provider", return_value=GoodProvider()):
        r = client.post("/chat", json={"message": "hi"},
                        headers=auth_headers(demo_token()))
    assert r.status_code == 200
    msgs = [json.loads(x) for x in r.text.strip().splitlines() if x.strip()]
    done = next(m for m in msgs if m["type"] == "done")
    assert done["status"] in ("ok", "done")
    assert done["provider"] == "groq"
    assert done["demo_mode"] is True


def test_both_providers_fail_honest(client):
    with patch("app.nodes.get_provider", return_value=BadAlwaysProvider()), \
         patch("app.nodes.get_fallback_provider", return_value=BadAlwaysProvider()):
        r = client.post("/chat", json={"message": "Rourkela se Ranchi 8 ton kal"},
                        headers=auth_headers(demo_token()))
    assert r.status_code == 200
    msgs = [json.loads(x) for x in r.text.strip().splitlines() if x.strip()]
    done = next(m for m in msgs if m["type"] == "done")
    assert done["status"] == "error"
    assert done["candidates"] == []
    reply = "".join(m.get("text", "") for m in msgs if m["type"] == "chunk")
    assert "unavailable" in reply.lower()


# ---------------------------------------------------------------------------
# M2 — strict production authentication
# ---------------------------------------------------------------------------
def _make_token(overrides: dict | None = None, secret: str | None = None,
                algorithm: str = "HS256") -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": "demo-shipper-01",
        "role": "authenticated",
        "iss": settings.clerk_expected_issuer or "disha-demo",
        "aud": settings.clerk_expected_audience or "authenticated",
        "iat": now,
        "exp": now + dt.timedelta(minutes=30),
    }
    if overrides:
        payload.update(overrides)
    return jwt.encode(payload, secret or settings.jwt_secret, algorithm=algorithm)


def test_wrong_algorithm_rejected():
    token = _make_token(algorithm="HS384")
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401


def test_missing_sub_rejected():
    token = _make_token({"sub": None})
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401


def test_issuer_mismatch_rejected_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "clerk_expected_issuer", "https://clerk.loadsaathi.app")
    token = _make_token({"iss": "https://evil.example"})
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401


def test_audience_mismatch_rejected_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "clerk_expected_audience", "loadsaathi")
    token = _make_token({"aud": "something-else"})
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401


def test_production_requires_clerk_contract():
    with pytest.raises(Exception):
        Settings(environment="production")


def test_production_requires_jwt_secret():
    with pytest.raises(Exception):
        Settings(environment="production",
                 clerk_expected_issuer="https://clerk.app",
                 clerk_expected_audience="loadsaathi")


def test_production_config_accepted_when_complete():
    s = Settings(environment="production",
                 clerk_expected_issuer="https://clerk.app",
                 clerk_expected_audience="loadsaathi",
                 supabase_jwt_secret="a" * 40)
    assert s.supabase_jwt_secret == "a" * 40
    assert s.demo_login_enabled is False


# ---------------------------------------------------------------------------
# M3 — demo-login isolation
# ---------------------------------------------------------------------------
def test_demo_login_allowed_in_isolated_demo(client):
    r = client.post("/auth/demo-login", json={"user_id": "demo-shipper-01"})
    assert r.status_code == 200


def test_demo_login_blocked_when_supabase_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://xyz.supabase.co")
    monkeypatch.setattr(settings, "supabase_anon_key", "anon-key")
    r = client.post("/auth/demo-login", json={"user_id": "demo-shipper-01"})
    assert r.status_code == 403


def test_demo_login_blocked_when_jwt_secret_set(client, monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", "s" * 40)
    r = client.post("/auth/demo-login", json={"user_id": "demo-shipper-01"})
    assert r.status_code == 403


def test_demo_login_disabled_in_production(client, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    r = client.post("/auth/demo-login", json={"user_id": "demo-shipper-01"})
    assert r.status_code == 403


def test_create_dev_token_respects_gate(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(HTTPException):
        create_dev_token("u1")
