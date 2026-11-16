"""JWT authentication — Clerk->Supabase JWT contract.

The existing LoadSaathi edge functions verify Clerk-Supabase JWTs with
HS256 against SUPABASE_JWT_SECRET, expected issuer/audience, expiry, and
role=authenticated. DISHA implements the same contract server-side. User id
always comes from the verified token `sub` claim — never from the request
body.
"""
from __future__ import annotations

import datetime as dt
import uuid

import jwt
from fastapi import Depends, Header, HTTPException, Request
from jwt import InvalidTokenError

from .config import settings


class TokenClaims:
    def __init__(self, sub: str, role: str, iss: str | None, aud: str | None):
        self.sub = sub
        self.role = role
        self.iss = iss
        self.aud = aud


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def create_dev_token(user_id: str, role: str = "authenticated", ttl_minutes: int = 60) -> str:
    """Mint a dev JWT for demo logins (only allowed when demo_login_enabled)."""
    if not settings.demo_login_enabled:
        raise HTTPException(status_code=403, detail="demo login disabled")
    now = _now()
    payload = {
        "sub": user_id,
        "role": role,
        "iss": settings.clerk_expected_issuer or "disha-demo",
        "aud": settings.clerk_expected_audience or "authenticated",
        "iat": now,
        "exp": now + dt.timedelta(minutes=ttl_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> TokenClaims:
    """Verify a Clerk->Supabase JWT. Raises HTTPException 401 on any failure."""
    if not token:
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={
                "verify_exp": True,
                "verify_iss": bool(settings.clerk_expected_issuer),
                "verify_aud": bool(settings.clerk_expected_audience),
            },
        )
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid or expired token")

    if settings.clerk_expected_issuer and payload.get("iss") != settings.clerk_expected_issuer:
        raise HTTPException(status_code=401, detail="unexpected issuer")
    if settings.clerk_expected_audience and payload.get("aud") != settings.clerk_expected_audience:
        raise HTTPException(status_code=401, detail="unexpected audience")
    if payload.get("role") != "authenticated":
        raise HTTPException(status_code=401, detail="role=authenticated required")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="missing sub claim")
    return TokenClaims(sub=str(sub), role="authenticated", iss=payload.get("iss"), aud=payload.get("aud"))


def require_user(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency -> verified user id (sub)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    claims = verify_token(token)
    return claims.sub


def require_token(authorization: str | None = Header(default=None)) -> tuple[str, str]:
    """FastAPI dependency -> (user_id, raw_jwt) so tool calls can forward the
    caller's JWT for RLS. The raw token is request-scoped and never stored."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    claims = verify_token(token)
    return claims.sub, token
