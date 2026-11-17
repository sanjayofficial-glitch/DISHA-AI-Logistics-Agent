"""DISHA FastAPI application.

Demo mode note: when no real LLM key is configured the service runs in
demo mode (deterministic planner, synthetic seed data). Every response
carries this fact; the UI shows a DEMO MODE badge.
"""
from __future__ import annotations

import asyncio
import collections
import json
import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import events as events_mod
from .auth import create_dev_token, require_token, require_user
from .config import settings
from .database import get_store
from .logging_config import configure_logging, get_logger
from .memory.store import MemoryStore
from .service import service

configure_logging()
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, version=settings.version)


@app.on_event("startup")
def _bootstrap() -> None:
    from .seed.bootstrap import ensure_demo_seeded

    ensure_demo_seeded()
    logger.info(
        "service_started",
        extra={
            "service": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
            "demo_mode": settings.demo_mode,
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_event_store = events_mod.EventStore()
_memory = MemoryStore()

# ---------------------------------------------------------------------------
# Rate limiting (in-memory sliding window)
# ---------------------------------------------------------------------------
_ratelimits: dict[tuple[str, str], collections.deque] = collections.defaultdict(collections.deque)


def _check_rate_limit(user_id: str, bucket: str, limit: int) -> None:
    key = (user_id, bucket)
    now = time.monotonic()
    dq = _ratelimits[key]
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= limit:
        raise HTTPException(status_code=429, detail="rate limit exceeded — please wait and retry")
    dq.append(now)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class DemoLoginBody(BaseModel):
    user_id: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    display_name: str = Field(default="", max_length=100)


class ChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: Optional[str] = Field(default=None, max_length=64)


class ApproveBody(BaseModel):
    thread_id: str = Field(min_length=4, max_length=64)


class FactBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class SearchBody(BaseModel):
    origin: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=100)
    weight_tonnes: Optional[float] = Field(default=None, gt=0)
    pickup_date: str = Field(default="", max_length=10)
    budget_inr: Optional[float] = Field(default=None, gt=0)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    db_ok = True
    try:
        store = get_store()
        store.get_market_stats()
    except Exception:
        db_ok = False
    return {
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "database": "reachable" if db_ok else "unreachable",
        "demo_mode": settings.demo_mode,
        "status": "ok",
    }


# ---------------------------------------------------------------------------
# Demo login (dev only)
# ---------------------------------------------------------------------------
@app.post("/auth/demo-login")
def demo_login(body: DemoLoginBody):
    if not settings.demo_login_enabled:
        raise HTTPException(status_code=403, detail="demo login disabled in this configuration")
    token = create_dev_token(body.user_id)
    return {"token": token, "user_id": body.user_id,
            "display_name": body.display_name or body.user_id,
            "demo_mode": True}


# ---------------------------------------------------------------------------
# Chat (streams the assistant reply as ndjson chunks)
# ---------------------------------------------------------------------------
@app.post("/chat")
async def chat(req: Request, body: ChatBody, user_id: str = Depends(require_user),
              auth: tuple[str, str] = Depends(require_token)):
    _check_rate_limit(user_id, "chat", settings.chat_rate_limit_per_min)
    token = auth[1]

    async def gen():
        result = await asyncio.to_thread(service.chat, token, body.message, body.thread_id)
        reply = result.get("reply") or ""
        # stream the completed reply in plain-text chunks (honest: no fake
        # token generation; the chunking is transport only)
        for i in range(0, len(reply), 80):
            chunk = reply[i:i + 80]
            yield json.dumps({"type": "chunk", "text": chunk}) + "\n"
            await asyncio.sleep(0.01)
        payload = {
            "type": "done",
            "status": result.get("status"),
            "thread_id": result.get("thread_id"),
            "provider": result.get("provider"),
            "approval_required": result.get("approval_required", False),
            "pending_action": result.get("pending_action"),
            "candidates": result.get("candidates", []),
            "search_mode": result.get("search_mode"),
            "demo_mode": result.get("demo_mode", settings.demo_mode),
        }
        yield json.dumps(payload) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


# ---------------------------------------------------------------------------
# Approval gate
# ---------------------------------------------------------------------------
@app.post("/approve")
def approve(body: ApproveBody, auth: tuple[str, str] = Depends(require_token)):
    _check_rate_limit(auth[0], "write", settings.write_rate_limit_per_min)
    result = service.approve(auth[1], body.thread_id)
    if result.get("status") == "forbidden":
        raise HTTPException(status_code=403, detail=result.get("error"))
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/reject")
def reject(body: ApproveBody, auth: tuple[str, str] = Depends(require_token)):
    result = service.reject(auth[1], body.thread_id)
    if result.get("status") == "forbidden":
        raise HTTPException(status_code=403, detail=result.get("error"))
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


# ---------------------------------------------------------------------------
# Threads / events
# ---------------------------------------------------------------------------
@app.get("/threads")
def list_threads(user_id: str = Depends(require_user), auth: tuple[str, str] = Depends(require_token)):
    return {"threads": service.list_threads(auth[1])}


@app.get("/threads/{thread_id}/events")
def thread_events(thread_id: str, auth: tuple[str, str] = Depends(require_token)):
    result = service.thread_events(auth[1], thread_id)
    if isinstance(result, dict) and result.get("status") == "forbidden":
        raise HTTPException(status_code=403, detail="forbidden")
    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=404, detail="thread not found")
    return {"thread_id": thread_id, "events": result}


# ---------------------------------------------------------------------------
# Memory (per-user facts, strict isolation)
# ---------------------------------------------------------------------------
@app.get("/memory")
def list_memory(user_id: str = Depends(require_user)):
    return {"facts": _memory.list_facts(user_id)}


@app.post("/memory")
def add_memory(body: FactBody, user_id: str = Depends(require_user)):
    fact = _memory.add_fact(user_id, body.text)
    return {"fact": fact}


@app.patch("/memory/{fact_id}")
def update_memory(fact_id: str, body: FactBody, user_id: str = Depends(require_user)):
    fact = _memory.update_fact(user_id, fact_id, body.text)
    if fact is None:
        raise HTTPException(status_code=404, detail="fact not found")
    return {"fact": fact}


@app.delete("/memory/{fact_id}")
def delete_memory(fact_id: str, user_id: str = Depends(require_user)):
    if not _memory.delete_fact(user_id, fact_id):
        raise HTTPException(status_code=404, detail="fact not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
@app.get("/metrics")
def metrics(user_id: str = Depends(require_user)):
    return service.metrics()


# ---------------------------------------------------------------------------
# Portals
# ---------------------------------------------------------------------------
@app.post("/market/search/trips")
def market_search_trips(body: SearchBody, user_id: str = Depends(require_user),
                        auth: tuple[str, str] = Depends(require_token)):
    """Scored trip search (read-only) — used by the Command Center."""
    store = get_store(auth[1])
    from .tools.marketplace import clean_city
    rows = store.search_trips(clean_city(body.origin), clean_city(body.destination))
    intent = {
        "origin": clean_city(body.origin),
        "destination": clean_city(body.destination),
        "weight_tonnes": body.weight_tonnes,
        "pickup_date": body.pickup_date,
        "budget_inr": body.budget_inr,
    }
    from .tools.matching import rank_candidates
    candidates = rank_candidates(rows, intent, "find_truck")
    return {"candidates": candidates, "count": len(candidates),
            "is_demo": True, "source": "synthetic_seed_data"}


@app.get("/portal/shipper/requests")
def shipper_requests(user_id: str = Depends(require_user), auth: tuple[str, str] = Depends(require_token)):
    store = get_store(auth[1])
    return {"requests": store.get_user_requests(user_id)}


@app.get("/portal/trucker/shipments")
def trucker_shipments(user_id: str = Depends(require_user), auth: tuple[str, str] = Depends(require_token)):
    store = get_store(auth[1])
    rows = store.get_pending_shipments()
    # Neutral scoring for browsing (route match only to the corridor)
    enriched = []
    from .tools.matching import score_candidate
    for row in rows:
        if row.get("status") != "pending":
            continue
        scored = score_candidate(
            row,
            {"origin": row.get("origin_city"), "destination": row.get("destination_city"),
             "budget_inr": row.get("budget_inr"), "pickup_date": row.get("pickup_date")},
            "find_load",
        )
        item = dict(row)
        item["score"] = scored["total_score"]
        item["factors"] = scored["factors"]
        item["explanation"] = scored["explanation"]
        item["is_demo"] = True
        item["source"] = "synthetic_seed_data"
        enriched.append(item)
    enriched.sort(key=lambda r: r["score"], reverse=True)
    return {"shipments": enriched}


@app.get("/portal/trucker/offers")
def trucker_offers(user_id: str = Depends(require_user), auth: tuple[str, str] = Depends(require_token)):
    store = get_store(auth[1])
    return {"offers": store.get_user_offers(user_id)}


@app.get("/portal/notifications")
def notifications(user_id: str = Depends(require_user), auth: tuple[str, str] = Depends(require_token)):
    store = get_store(auth[1])
    try:
        rows = store._q("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                         (user_id,)) if hasattr(store, "_q") else []
    except Exception:
        rows = []
    return {"notifications": rows}
