# DISHA Implementation Baseline

**Repository:** https://github.com/sanjayofficial-glitch/DISHA-AI-Logistics-Agent
**Audit date:** 17 Nov 2026
**Status:** VERIFIED baseline snapshot (read-only audit; no code changed)

---

## 1. Git state (verified)

| Item | Value |
|---|---|
| Current branch | `feature/disha-command-center` |
| HEAD | `d51b84272f0cefb300a224940cbd778a1462caf2` |
| Working tree | clean (no staged/unstaged changes) |
| Upstream | none — branch NOT pushed (`git branch -vv` shows no `[origin/...]`) |
| Remotes | `origin` → `https://github.com/sanjayofficial-glitch/DISHA-AI-Logistics-Agent.git` |
| History | `d51b842` ← `c6944cb` (functional-readiness) ← `61035ec` ← `76a456d` (preflight-hardening) ← `0b09030` (default branch) |

Verified commands:
```
git status --short --branch            → ## feature/disha-command-center  (clean)
git rev-parse HEAD                     → d51b84272f0cefb300a224940cbd778a1462caf2
git branch -vv                         → * feature/disha-command-center d51b842 …  (no upstream)
git remote -v                          → origin https://github.com/sanjayofficial-glitch/DISHA-AI-Logistics-Agent.git (fetch/push)
git diff --stat                        → (empty)
git diff --cached --stat               → (empty)
```

## 2. Backend inventory (`disha-agent/app/`)

| Module | Contents (verified) |
|---|---|
| `main.py` | FastAPI app, lifespan bootstrap, CORS allowlist, rate limiting (chat 30/min, write 10/min), JSON logging. Routes: `/health`, `/auth/demo-login`, `/chat` (ndjson stream), `/approve`, `/reject`, `/threads`, `/threads/{id}/events`, `/memory` GET/POST/PATCH/DELETE, `/metrics`, `/market/search/trips`, `/market/quote`, `/market/stats`, `/market/trips`, `/approvals`, `/portal/shipper/requests`, `/portal/trucker/shipments`, `/portal/trucker/offers`, `/portal/negotiations/{request_id}`, `/portal/notifications`. `_status_explained()` map. |
| `auth.py` | JWT verify (HS256, expiry, `role=authenticated`, issuer/audience when configured), `create_dev_token` (demo only), `require_user`/`require_token` dependencies. |
| `config.py` | pydantic-settings; `environment`, LLM keys, Supabase URL/anon/secret, Clerk issuer/audience, CORS, rate limits, data dir; **production fail-closed validator** (requires issuer+audience+JWT secret); `demo_mode`, `supabase_configured`, `demo_login_enabled`. |
| `service.py` | `AgentService` — `chat`, `approve`, `reject`, `thread_events`, `list_threads`, `pending_approvals`, `metrics`; request-scoped JWT via contextvars; owner check on approve/reject. |
| `graph.py` | LangGraph StateGraph: `understand → discover → rank → coordinate → execute`, `interrupt_before=["execute"]`, `SqliteSaver` checkpointer. |
| `nodes/__init__.py` | System/INTENT prompts; `understand` (demo planner or LLM w/ retry+fallback), `discover`, `rank`, `coordinate` (builds `pending_action`), `execute` (runs gated tool), `_price_quote_reply`. |
| `tools/marketplace.py` | Registry of 10 tools (Pydantic schemas, read_only flag): search_trips, search_shipments, get_market_stats, create_shipment_request, create_transporter_offer, accept_offer, confirm_request, send_notification, register_vehicle_availability, make_counter_offer. `clean_city` strips non-alnum. |
| `tools/matching.py` | Deterministic scorer: route 35%, capacity 25%, price 20%, date 10%, reliability 10%; per-factor explanations; ranks only (no feasibility/PTL). |
| `tools/pricing.py` | Estimate engine: demo corridor distances + ₹28/km base × 1.35 fuel/toll, rounded to ₹10; labeled `is_estimate`; unknown route → honest unavailable. |
| `tools/registry.py` | `Tool` wrapper (schema validation, timeout, result envelope, `is_demo`,`source`). |
| `providers/` | `BaseProvider`, `ProviderError(retryable)`; `DemoProvider` (deterministic planner), `GeminiProvider` (REST), `GroqProvider` (OpenAI-compatible); `get_provider` / `get_fallback_provider`. |
| `memory/store.py` | SQLite facts, per-user filtered, caps (20). |
| `events.py` | SQLite event store (node transitions) + metrics computation. |
| `database.py` | `SCHEMA` (trips, shipments, requests, shipment_requests, notifications, facts, events, negotiations), `SQLiteStore`, `SupabaseStore` (anon key + caller JWT; service-role never used), `get_store()`. |
| `context.py` | Request-scoped contextvars (user id + JWT; never persisted). |
| `logging_config.py` | JSON formatter with sensitive-key redaction (`token`, `authorization`, `api_key`, `apikey`, `secret`, `password`, `jwt`, `credential`, `private_key`). |

## 3. Frontend inventory (`frontend/src/`)

| Path | Contents (verified) |
|---|---|
| `App.tsx` | Auth gate (`DemoLogin`), then `AuthUserProvider` + `AppShell`. |
| `appShell/AppShell.tsx` | Navy sidebar (desktop) + mobile drawer; 10-section nav; header with demo badge/role/logout. |
| `lib/api.ts` | Typed client: session (localStorage demo token), `chat` (buffers ndjson), approve/reject, threads/events, memory, metrics, market search, quote, stats, trips, approvals, negotiations, notifications. |
| `pages/` | Overview, AiAssistant (wraps ChatView), Shipments (role-aware), Vehicles (table + gated publish), Matching, Pricing (EstimatePanel), Negotiations (history + counter-offer), Approvals (list + approve/reject), Activity, Settings. |
| `components/` | ChatView (streaming reveal, voice, CandidateCard, ApprovalCard), CommandCenter (legacy), ShipperPortal, TruckerPortal, DemoLogin, DemoBadge, authContext. |
| `hooks/useVoice.ts` | Web Speech input + SpeechSynthesis replies, mute persisted. |
| `ui/primitives.tsx` | Card, StatCard, Badge, PageHeader, EmptyState, ScoreBar, EstimatePanel. |
| `tailwind.config.ts` | `disha` orange + new `navy` palette. |

## 4. Persistence (verified)

- **SQLite** `disha-agent/data/disha.db` (WAL): marketplace tables + facts + events + negotiations + LangGraph checkpoints (`SqliteSaver`). Persists across restarts.
- **Supabase adapter** exists but is **not active** in current config (no `SUPABASE_URL`/`SUPABASE_ANON_KEY` set). Activation is purely env-driven (`get_store()`, database.py:562).
- Demo seed (`app/seed/`) carries `[DEMO]`/`synthetic_seed_data` markers on every row.

## 5. Deployment config (verified)

- `Dockerfile` — python:3.12-slim, installs requirements, uvicorn on `$PORT` (8080), `/health` HEALTHCHECK.
- `.env.example` — placeholders only (no real values); documents production fail-closed rules.
- `requirements.txt` — fastapi, uvicorn, pydantic(-settings), httpx, PyJWT, langgraph, langgraph-checkpoint-sqlite, pytest, pytest-asyncio.
- No CI/deploy workflow beyond `.github/workflows/ci.yml` (pytest + frontend build).

## 6. Tests (executed this session)

```
Command:  .\.venv\Scripts\python.exe -m pytest tests -q
Result:   73 passed, 1 warning in ~6.7s  (exit code 0)
Command:  npm run build   (frontend)
Result:   exit code 0 (tsc --noEmit && vite build)
```

## 7. Verified facts vs assumptions

| Item | Verdict |
|---|---|
| 73 tests pass; frontend build passes | VERIFIED (commands above) |
| Approval gate: `interrupt_before=["execute"]`, approve/reject owner-checked | VERIFIED (graph.py:70; service.py:62–109) |
| Demo data labeled synthetic; demo-login isolated | VERIFIED (config/settings; seed markers) |
| No secrets committed; logging redacts | VERIFIED (secret scan; logging_config.py) |
| Supabase table/column names match LoadSaathi production schema | **ASSUMED / UNVERIFIED** (production not accessible; based on audit doc) |
| LoadSaathi RLS policies protect adapter writes | ASSUMED (adapter forwards caller JWT; RLS not testable without project) |
| Matching ≈ feasibility | FALSE (ranking only — documented limitation) |
