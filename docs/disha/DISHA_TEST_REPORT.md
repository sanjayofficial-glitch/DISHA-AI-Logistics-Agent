# DISHA Test Report

**Date:** 2026-11-17 · **Run:** `cd disha-agent && .venv\Scripts\python -m pytest tests -q`
**Result: 39 passed, 0 failed** (plus typecheck + frontend build).

| Suite | Covers | Result |
|---|---|---|
| `test_health.py` | /health, demo mode flag, no secret leakage, auth required | ✅ 4/4 |
| `test_auth.py` | HS256 verify, expiry, wrong signature, missing role, endpoint enforcement | ✅ 6/6 |
| `test_chat.py` | find-truck candidates, clarification, create-request approval gate, approve writes, reject writes nothing, cross-user approve 403, cross-user events 403, full two-sided offer/accept/confirm flow | ✅ 8/8 |
| `test_memory.py` | lifecycle, strict per-user isolation (list/update/delete), "remember" via chat | ✅ 3/3 |
| `test_tools.py` | registry, injection attempts (SQL + comment), payload validation, city sanitization | ✅ 5/5 |
| `test_matching.py` | weight constants, factor set, weighted sum, ranking order, explanations, empty input | ✅ 4/4 |
| `test_events.py` | per-node events, owner-only, metrics endpoint shape | ✅ 4/4 |
| `test_portals.py` | shipper requests, scored trucker shipments, offers, notifications | ✅ 4/4 |
| `test_failover.py` | failing provider → honest error, demo mode labeled | ✅ 2/2 |

Frontend: `npm run typecheck` ✅ · `npm run build` ✅ (dist emitted).

## Manual verification performed

- Backend boot: `uvicorn app.main:app` → `GET /health` 200, `database: reachable`,
  `demo_mode: true`.
- Frontend dev server: `npm run dev` → HTTP 200 at `http://localhost:5173`.
- Full demo corridor flow exercised through the API (shipper request → offer →
  accept → confirm) with event trail visible.

## Known limitations

- Visual browser click-through of all portals was not performed in this session
  (no Playwright installed); the flows are covered at the API level and the UI
  builds cleanly. A quick manual pass at `http://localhost:5173` is recommended.
- Supabase live store and real LLM providers require credentials to test.
