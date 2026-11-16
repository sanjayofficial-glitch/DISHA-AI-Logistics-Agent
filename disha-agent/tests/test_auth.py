"""Auth contract tests — HS256, issuer/audience, expiry, role required."""
from __future__ import annotations

import datetime as dt

import jwt

from app.auth import verify_token
from app.config import settings
from .conftest import auth_headers, demo_token


def _make_token(overrides: dict | None = None, secret: str | None = None) -> str:
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
    return jwt.encode(payload, secret or settings.jwt_secret, algorithm="HS256")


def test_verify_token_ok():
    claims = verify_token(_make_token())
    assert claims.sub == "demo-shipper-01"
    assert claims.role == "authenticated"


def test_expired_token_rejected():
    token = _make_token({"exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)})
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401


def test_wrong_signature_rejected():
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        verify_token(_make_token(secret="wrong-secret"))
    assert exc.value.status_code == 401


def test_missing_role_rejected():
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        verify_token(_make_token({"role": "anonymous"}))
    assert exc.value.status_code == 401


def test_endpoint_rejects_bad_token(client):
    r = client.get("/threads", headers=auth_headers("not.a.jwt"))
    assert r.status_code == 401


def test_endpoint_accepts_valid_token(client):
    r = client.get("/threads", headers=auth_headers(demo_token()))
    assert r.status_code == 200
