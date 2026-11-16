# DISHA Architecture

**Date:** 2026-11-17 · **Branch:** `feature/disha-langgraph` · **Status:** implemented

## 1. System at a glance

| Component | Technology | Role |
|---|---|---|
| Backend agent | Python 3.11 + FastAPI + LangGraph (1.2.x) | Orchestration, approval gate, tools, memory |
| LLM providers | Gemini REST (primary), Groq (fallback), deterministic demo planner | Language understanding (only when keys exist) |
| Matching engine | Pure Python, deterministic | Route 35% · capacity 25% · price 20% · date 10% · reliability 10% |
| Storage | SQLite demo store (local) ↔ Supabase PostgREST store (when configured) | Marketplace rows, memory, events, checkpoints |
| Auth | JWT HS256, Clerk→Supabase contract | `sub` from verified token; per-user isolation |
| Frontend | React 19 + Vite + Tailwind (in `frontend/`) | Chat view, Command Center, Shipper/Trucker portals, voice |
| Voice | Browser Web Speech API | Utterance-based transcription + speech synthesis (mutable) |

## 2. Request flow (LangGraph)

```
START → understand → discover → rank → coordinate → (interrupt before) execute → END
```

- **understand** — provider (Gemini/Groq via REST, or demo planner) extracts structured
  intent. Missing fields produce exactly one clarification and end the turn.
  Explicit "remember that …" writes a memory fact (user-initiated only).
- **discover** — read-only tools `search_trips` / `search_shipments` run against the
  store with the caller's JWT. Search failures are reported honestly.
- **rank** — deterministic engine scores candidates; per-factor explanations always
  accompany results.
- **coordinate** — for write intents (create request, send offer, accept offer,
  confirm request) a `pending_action` is staged and `approval_required` is set.
  The graph is compiled with `interrupt_before=["execute"]`.
- **execute** — runs **only** after `POST /approve` resumes the thread; the JWT is
  revalidated and the caller must own the thread (403 otherwise).

## 3. Security boundaries

- The raw JWT is request-scoped (`contextvars`) and is **never** stored in graph
  state or checkpoints; it is refreshed and revalidated on resume.
- All user queries are parameterized. City inputs are sanitized to letters/digits/
  spaces before use, so injection attempts resolve to safe empty results.
- Demo login (`POST /auth/demo-login`) is only enabled when no real
  `SUPABASE_JWT_SECRET` is configured. RLS remains the authorization boundary when
  the Supabase store is active.
- No service-role key anywhere; the Supabase client sends `apikey` (anon) +
  `Authorization: Bearer <caller JWT>`.
- Real provider failures surface as a clean 503/error state — never a fake reply.
  Demo mode is a separate, labeled operation mode (`provider: demo`, demo badge).

## 4. Honesty rules implemented

- Every tool/result envelope carries `is_demo: true` + `source: synthetic_seed_data`
  in demo mode; the UI shows a persistent **demo data (synthetic)** badge.
- Metrics are computed from the recorded events store; unavailable values render as
  "unavailable", never estimates.
- No write happens without explicit approval; a rejected action writes nothing.
- Cross-user access (threads, events, memory, approval) is rejected with 403/404.

## 5. Storage migration path

SQLite (local demo) ↔ Supabase PostgreSQL: both implement the same
`MarketplaceStore` interface; switching is a `.env` change (`SUPABASE_URL`,
`SUPABASE_ANON_KEY`). The LangGraph checkpointer can be swapped for the Postgres
checkpointer at deployment time (see deployment guide) — call sites do not change.
