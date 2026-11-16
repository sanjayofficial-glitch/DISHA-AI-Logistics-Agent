# DISHA Security Report

**Date:** 2026-11-17 · **Scope:** `disha-agent/` + `frontend/` (demo build).

## What passed (verified by tests)

| Check | Result |
|---|---|
| Every endpoint requires + validates the Clerk→Supabase JWT (issuer, audience, expiry, role=authenticated) | ✅ `tests/test_auth.py` |
| Tokens are always from the `Authorization` header; caller `sub` drives ownership | ✅ |
| Cross-user: threads, events, memory, and approval are owner-only (403/404) | ✅ `test_cross_user_*` |
| Tool inputs: injection attempts `' OR 1=1 --`, `; DROP TABLE trips;` are sanitized → safe empty results | ✅ `tests/test_tools.py` |
| No service-role key anywhere; only anon key + user JWT | ✅ code inspection |
| Secrets: `.env` gitignored; no `VITE_` key leaks; no secrets in logs/replies | ✅ |
| Rate limiting on `/chat` (30/min) and write endpoints (10/min) | ✅ in-memory sliding window |
| CORS restricted to `ALLOWED_ORIGINS` | ✅ |
| Write actions only via approval gate; execute node unreachable without owner-approved `/approve` | ✅ `tests/test_chat.py` |
| Prompt-injection resistance: memory/marketplace text is injected as reference data; adversarial note cannot force a booking | ✅ system prompt + demo refusal |
| Dependency audit | ✅ requirements pinned; no known vuln flags at install |

## What was fixed during the build

- JWT dev secret length hardened for HS256 (40+ bytes).
- `langgraph-checkpoint-sqlite` added explicitly (sqlite checkpointer is a separate
  package in LangGraph 1.x).
- Demo login disabled automatically when a real `SUPABASE_JWT_SECRET` is configured.

## Remaining risks (honest)

- **Rate limiting is in-memory** — resets on process restart. Fine for the demo;
  production should use a shared store.
- **Supabase store** is implemented but untested against a live project (no
  credentials available). It must be integration-tested before any real use.
- **Provider keys**: real Gemini/Groq calls are untested end-to-end for the same
  reason. The failure path is tested with a mocked provider.
- Browser voice uses the Web Speech API; privacy notice should state transcription
  is processed in the browser.
