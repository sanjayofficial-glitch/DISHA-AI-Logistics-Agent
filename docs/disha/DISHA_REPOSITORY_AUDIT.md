# DISHA Repository Audit

**Phase 0 — Repository Audit (docs only, no feature code)**
- Audit date: 2026-11-17
- Workspace: `D:\disha` (branch `feature/disha-langgraph`, local repo with **zero commits**, no remote)
- Authoritative reference: `DISHA_Free_Build_Playbook.md` (chapters 2, 5, 7 Phase 0)
- Method: every claim below was verified by reading the actual file or running the command. Nothing is assumed from the playbook alone.

---

## 1. Executive finding

The DISHA workspace at `D:\disha` is a **docs-only staging repository**. It does **not** contain the LoadSaathi production app. The production app — the React 19 / Vite frontend, the Supabase Edge Functions (including Freddy / `agent-router`), the database migrations with RLS policies, and the Vercel deployment — lives in a **separate repository** on the same machine:

> `D:\Users\sanja\dyad-apps\LOAD-SAATHI-DISHA`

(currently on branch `feature/disha-coordinator`, with a `main` branch and origin remote).

This split matters for every later phase:

- The **backend** (`disha-agent/`) is planned inside `D:\disha` per the sibling Phase 1 prompt.
- The **frontend** work (Phases 6–8: chat view, Command Center, portals) must land inside the **production repo** (`supabase/src/…`), because that is where the React app lives.
- No schema/table existence claim in this audit is a guess: the baseline migration `20250601_baseline_schema.sql` was read in full, and the latest RLS state was read from migration `20261019120000_rls_initplan_and_clerk_auth_fix.sql`.

---

## 2. Workspace inventory (`D:\disha`) — file-by-file

| Path | Size | What it is | Verdict |
|---|---|---|---|
| `DISHA_Free_Build_Playbook.md` | 67,875 B (1,248 lines) | Single working document: free-resource stack, Day-Zero checklist, 13 phase prompts, honesty rules, cost ledger | **Keep as authoritative reference.** Read in full. |
| `.gitignore` | 364 B | Python venvs, `__pycache__/`, `.env*`, `node_modules/`, OS files, build artifacts, IDE, `.orca-scratch/`, `.orca-prompts/` | **Reusable** (created by the Freebuff housekeeping pass). |
| `README.md` | 777 B | One-paragraph overview, pointer to playbook and `docs/disha/`, branch rule | **Reusable.** |
| `.orca-prompts/opencode_phase0.md` | — | This task's prompt | Owned by OpenCode Phase 0. |
| `.orca-prompts/kilo_phase1.md` | — | Sibling prompt: backend skeleton `disha-agent/app/` (FastAPI, auth, /health, Docker) | Owned by Kilo. Contract for Phase 1. |
| `.orca-prompts/cline_tests.md` | — | Sibling prompt: `disha-agent/tests/`, `demo/seed_demo_data.py`, `disha-agent/README.md` | Owned by Cline. Contract for tests/demo. |
| `.orca-prompts/freebuff_housekeeping.md` | — | Sibling prompt: root `.gitignore`, `README.md`, `DAY_ZERO_CHECKLIST.md` | Already executed (see below). |
| `docs/disha/DAY_ZERO_CHECKLIST.md` | — | Day-Zero verification results (2026-11-17) | **Reusable evidence.** See gaps in §3. |
| `.freebuff/project-id` | 36 B | `bdaabee0-c9cf-4ab7-a31d-5299ad624294` (agent metadata) | Irrelevant to the build; leave alone. |
| `.git/` | — | Fresh repo: no commits, no remote, branch `feature/disha-langgraph` checked out | First commit should be these docs + prompts only. |

No other files exist in `D:\disha` (full recurse scan incl. hidden files).

---

## 3. Day-Zero verification status (from `DAY_ZERO_CHECKLIST.md`, read directly)

| Check | Result | Note |
|---|---|---|
| `python --version` | 3.11.9 | **Below 3.12 target — upgrade before Phase 1.** |
| `git --version` | 2.56.0.windows.4 | OK |
| Branch | `feature/disha-langgraph` | OK (verified again this audit) |
| Node.js | v24.20.0 | OK (≥22 required by LoadSaathi `package.json` engines) |
| pnpm | 11.8.0 | OK (LoadSaathi uses `pnpm@9.12.3` via `packageManager`) |
| Playbook present | Yes | OK |
| OpenCode login, Gemini/Groq keys, second Supabase project, Cloud budget alert | Not verified | Account-level steps; must exist before Phase 2 / Phase 11 respectively |

---

## 4. Production app inventory (`D:\Users\sanja\dyad-apps\LOAD-SAATHI-DISHA`) — file-by-file findings

### 4.1 Repository shape
- `package.json`: name `load-saathi`, package manager `pnpm@9.12.3`, engines Node ≥22. Scripts: `dev`, `build` (with `prebuild` validators: `validate-env.mjs`, blog meta, sitemap, llms routesgen `build` runs `vite build` + `prerender.mjs` + `smoke.mjs`), `lint` (eslint), `typecheck` (`tsc --noEmit`), `format`/`format:check` (prettier), `test`/`test:watch`/`test:coverage` (vitest), **`check` = `pnpm lint && pnpm typecheck && pnpm test && pnpm build`** — this is the "pnpm check" gate the playbook demands after every meaningful change.
- Frontend stack (verified in `package.json`): React 19.2.3, Vite 6.4.4, TypeScript 5.5.3, Tailwind 3.4.11, Clerk `@clerk/clerk-react` 5.61.10, `@supabase/supabase-js` ^2.99.3, recharts, leaflet, lucide-react, zod, react-router-dom 7.
- Source root is **`supabase/src/`** (not `src/`): `components/`, `pages/`, `hooks/`, `lib/`, `contexts/`, `integrations/`, `config/`, `data/`, `features/`, `styles/`, `theme/`, `types/`, `utils/`, `test/`.
- Vercel serverless: `api/agent.js` (edge runtime, SPA route fallback + agent proxy), `api/site.js`, `api/lead-quote.js`, `api/cron/daily.js`, `api/cron/diesel.js`; `vercel.json` (HSTS/CSP headers, rewrites to `/api/agent.js`, crons).

### 4.2 Supabase Edge Functions (`supabase/functions/`)
14 functions: `admin-secrets`, `agent-router`, `credit-insights`, `credit-score`, `demand-forecast`, `fetch-diesel-price`, `fraud-detect`, `gemini-proxy`, `get-fuel-price`, `lead-alert`, `match-ml`, `ops-daily-digest`, `price-predict`, `_shared`.

- **`agent-router/` — the Freddy agent (must never be modified).** Verified `handler.ts` (763 lines): kill switch `FREDDY_ENABLED` (fail-closed), per-IP rate limit 10/min, strict body contract, `verifyClerkJwt` before anything, no service-role key, sanitized errors. It already contains an **opt-in, read-only "Disha workflow"** (`disha: true`): `shipment_analyst` (LLM extracts filters) → `matching_specialist` (`searchMarket`) → `disha_coordinator` (LLM explanation with deterministic fallback). All reads use the caller's verified JWT + `SUPABASE_ANON_KEY`.
- **`_shared/searchMarket.ts` — the read-only marketplace query contract (verified, 531 lines).** Fixed SELECT allowlist, `status in (active, in_transit)`, order `departure_date.asc`, limit 50, timeout 8s, strict filter validation (unknown keys rejected; text ≤80 chars, NUL rejected, `ilike` wildcards escaped via `escapeLikePattern`), bounded numerics, sanitized failure reasons, `Authorization: Bearer <caller JWT>` + `apikey: <anon>`. **This is the contract DISHA's `search_trips` must reuse.**
- **`_shared/verifyClerkJwt.ts` — the JWT contract (verified, 175 lines).** HS256 pinned (rejects `none`/asymmetric), `exp` required, `nbf`/`iat` honored with 30s skew, `role=authenticated` required, `iss` exact match, `aud` must intersect expected set, `sub` returned byte-exact (Clerk `user_*` ids preserved, never coerced). Config injected by caller from env: `SUPABASE_JWT_SECRET`, `FREDDY_EXPECTED_ISSUER`, `FREDDY_EXPECTED_AUDIENCE`. **Phase 1 `auth.py` must port this exact contract.**
- **`_shared/llmChat.ts` — the provider chain (verified, 271 lines).** Gemini → Groq → OpenRouter in order; every key optional (`not_configured` when absent); 429 → rate-limited; other failures → try next provider; hard cap `LLM_MAX_PROMPT_CHARS=4000`, `LLM_MAX_OUTPUT_CHARS=2000`, `LLM_MAX_TOKENS=400`, timeout 12s; closed failure vocabulary; never throws; provider + model names are constants here (Gemini model `gemini-flash-lite-latest`, Groq `openai/gpt-oss-120b`, OpenRouter two `:free` NVIDIA models). `gemini-proxy` mirrors the same chain.
- **`_shared/dishaWorkflow.ts`** — intent classifier, analyst/coordinator prompts, `DishaStepEvent` trace shape (step, status, summary, durationMs), deterministic explanation fallback. `_shared/edgeHelpers.ts` — CORS, error responses, rate limiter, bearer extraction. `osrm.ts`, `fuel.ts` — distance/price helpers.
- Tests exist alongside functions: `searchMarket_test.ts`, `verifyClerkJwt_test.ts`, `llmChat_test.ts`, `dishaWorkflow_test.ts`, `agent-router/handler_test.ts` (Deno-style, injectable fetch/env, network-free).

### 4.3 Database schema (`supabase/migrations/`, 60+ files)
Read in full: `20250601_baseline_schema.sql` (baseline, idempotent). Exact tables/columns/status values:

| Table | Key columns | Status CHECK values |
|---|---|---|
| `trips` | `trucker_id` (text → users.id), `origin_city`, `destination_city`, `departure_date`, `available_capacity_tonnes` (>0), `price_per_tonne` (>0), `vehicle_type`, `vehicle_number`, `origin_state`, `destination_state`, coords, `estimated_distance_km`, `estimated_duration_min` | `active`, `in_transit`, `delivered`, `completed`, `cancelled` |
| `shipments` | `shipper_id`, `origin_city`, `destination_city`, `departure_date`, `goods_description`, `weight_tonnes` (>0), `pickup_address`, `delivery_address`, `budget_per_tonne` (>0), coords | `pending`, `matched`, `in_transit`, `delivered`, `completed`, `cancelled` |
| `requests` | `trip_id`, `shipper_id`, `receiver_id` (trucker), `goods_description`, `weight_tonnes`, `pickup_address`, `delivery_address`, `shipment_id?` | `pending`, `accepted`, `declined` |
| `shipment_requests` | `shipment_id`, `trucker_id`, `shipper_id`, `proposed_price_per_tonne?`, `message?` | `pending`, `accepted`, `declined`, `cancelled` |
| `notifications` | `user_id`, `message`, `is_read`, `type?`, `related_trip_id?`, `related_shipment_request_id?` | — |
| `messages` | `sender_id`, `recipient_id`, `content`, `request_id?`, `shipment_request_id?`, `is_read` | — |

Indexes exist for the discovery queries (`idx_trips_status_origin_dest`, `idx_shipments_status_origin_dest`, etc.). All six tables are in the `supabase_realtime` publication.

### 4.4 RLS end-state (verified from `20261019120000_rls_initplan_and_clerk_auth_fix.sql` + hardening history)
- Identity: Clerk `sub` = `users.id` (text). Helper `current_clerk_user_id()` = `auth.jwt()->>'sub'`. `auth.uid()` is deliberately **not** used (throws on Clerk-format ids).
- `trips`: SELECT `USING (true)` for authenticated ("Anyone can see active trips"); INSERT/UPDATE/DELETE only for owner trucker (or admin). Anon SELECT limited to active trips for share pages.
- `shipments`: SELECT only `status='pending'` or own; INSERT/UPDATE/DELETE owner-only.
- `requests` / `shipment_requests`: SELECT/UPDATE only for the two participants; INSERT owner-only (shipper / trucker respectively); UPDATE `WITH CHECK` re-asserts ownership (blocks reassignment).
- `notifications` / `messages`: participant-only SELECT/UPDATE; insert as sender/user.
- `users`: insert own profile; update own or admin (admin gated with `WITH CHECK`); authenticated can read all users (needed for joins).
- System/service writes (`notifications`, `credit_scores`, `price_history`, `ml_match_log`, …) are `TO service_role` only — **no authenticated path** (fixed in `20260927_tighten_overly_permissive_rls_policies.sql`).
- DML via `SECURITY DEFINER` RPCs exists (`insert_trip`, `insert_shipment`, `insert_shipment_request`, `create_notification`, …) — the app's own write path. A 2026-09-27 audit noted "repo-wide scan shows zero direct `.insert/.update` chains reaching those tables" (all writes go through these RPCs).

### 4.5 Existing AI integrations
Gemini / Groq / OpenRouter all already integrated: `_shared/llmChat.ts` + `gemini-proxy` edge function. Model names are constants today (see §4.2); the playbook wants models in env (`GEMINI_MODEL`) for the new backend — this is a *new* requirement for `disha-agent`, not a change to the edge function.

### 4.6 Existing tests & checks
- `supabase/src/test/` — 12 vitest files incl. `setup.ts`, plus `disha.test.ts` and `dishaRunStore.test.ts`.
- Edge function tests (Deno) — see §4.2.
- Gates: `pnpm check` (lint+typecheck+test+build) at repo root; `pytest` planned in `disha-agent`.

### 4.7 Environment & secrets
- Only `.env.example` exists (placeholders). **No `.env`/real key files found in either repo** (recursive scan).
- `vercel.json` enforces security headers (HSTS, CSP report-only, nosniff, permissions policy).

### 4.8 Existing Disha UI layer (important overlap)
The production app already ships a **branded "Disha" coach UI** behind flag `VITE_DISHA_UI=false` (default off): `src/components/Disha.tsx`, `DishaCharacter`, `DishaSpeechBubble`, `DishaAskPanel`, `DishaSpotlight`, `DishaHelpPanel`, `DishaMascot`, `DishaGuideProvider`, `DishaGuideEngine`, `DishaContext`, `DishaOnboardingTips`; hooks `useDishaCoordinator`, `useDishaGuide`; lib `dishaRequest.ts` (response types mirror `dishaWorkflow.ts`) and `dishaRunStore.ts`; tests. This is the read-only "Ask Disha" inside Freddy's bubble. **The competition product (chat view, Command Center, portals) is a separate, larger surface; it must not be confused with this coach layer, and this layer must not be broken.**

---

## 5. What is reusable

1. **Playbook architecture decisions** — weights, approval gate, two-sided flow, trace shapes, free-tier stack.
2. **`verifyClerkJwt.ts` contract** — port to Python `auth.py` (HS256, exp/nbf/iat, role, iss/aud, sub byte-exact).
3. **`searchMarket.ts` contract** — port to `disha-agent` tool `search_trips` (validation, escaping, select allowlist, ordering, limit, sanitized errors, anon+JWT headers).
4. **`llmChat.ts` provider-chain semantics** — Gemini primary, Groq fallback, OpenRouter emergency; key-optional fail-closed behavior; bounds; 503/`unavailable` semantics. (Python reimplementation; do not reuse Deno code directly.)
5. **RLS + Clerk JWT identity mapping** — user id = `sub`; no service-role anywhere; write approval must target owner-scoped rows (RLS is the enforcement).
6. **Existing event-trace vocabulary** — `DishaStepEvent` (step/status/summary/durationMs) is the vocab for the Command Center.
7. **Day-Zero checklist + `.gitignore` + root README + branch rule** — already in place.
8. **Existing frontend Disha components/flag** — reference for Phase 6 styling and for avoiding duplication/conflict.

## 6. What must be built new

- `disha-agent/` Python backend: FastAPI app (`main.py`, `config.py`, `auth.py`, `database.py`, `graph.py`, `state.py`), `nodes/`, `tools/`, `memory/`, `tests/`, `requirements.txt`, `Dockerfile`, `.dockerignore`, `.env.example`, `README.md`.
- LangGraph orchestration with checkpointing (SQLite locally) + `interrupt_before=["execute"]` approval gate; `/approve`, `/reject` endpoints; events store; `/chat` streaming.
- Deterministic matching engine (pure Python; route 35 / capacity 25 / price 20 / date 10 / reliability 10).
- Frontend `src/disha/` in the production repo: chat view, Command Center, Shipper/Trucker portals.
- Demo seed (`disha-agent/demo/seed_demo_data.py`, synthetic, SQLite-only, `--demo` guard).
- Later-phase reports: security report, test report, deployment guide, QA report + storyboard.

## 7. Not-a-file findings (checked, absent)

- No `src/disha/` exists yet.
- `disha.diff` at the production repo root exists but is **0 bytes** (empty placeholder).
- **Concurrent sibling activity observed (2026-11-17 02:24):** `D:\disha\disha-agent/` appeared with `tests/test_health_auth_isolation.py`, `tests/__init__.py`, `data/`, `demo/` — consistent with the Kilo Phase 1 prompt starting in parallel. No `app/` or backend code existed at audit close. This phase made no changes there; Phase 1 owns that path.
- No secrets, no `.env`, no service-role references in either repo.
- No Cloud Run / Docker configuration exists yet (Phase 11 output).

## 8. Audit completeness statement

Every statement above traces to a file or command read during this audit. Items that could **not** be verified (because the live Supabase project isn't reachable from this machine) are: the *actual runtime* RLS deployment state vs. migration history, live table row counts, and the real Clerk/Supabase project URLs — the migration files are authoritative for intent, but a live `pg_policies` snapshot is recommended before Phase 5 writes. This is recorded as an open verification item in the risk register.
