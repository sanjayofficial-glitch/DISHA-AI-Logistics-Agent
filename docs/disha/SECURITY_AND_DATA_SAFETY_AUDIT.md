# DISHA Security & Data-Safety Audit

**Audit date:** 17 Nov 2026 · **Scope:** local DISHA repo @ `d51b842` (read-only; no code changed)
**Method:** source inspection + live smoke tests + full pytest suite. Each risk area below is rated by severity and includes reproduction steps where relevant.

---

## Risk Area 1 — SupabaseStore field mismatches with LoadSaathi schema

- **Status: ASSUMED / UNVERIFIED (cannot verify without production access).**
- Findings: `SupabaseStore` (database.py:407–556) writes/reads these tables/columns:
  - `trips`: transporter_user_id, origin_city, destination_city, departure_date, capacity_tonnes, price_per_tonne, vehicle_type, reliability_score, status
  - `shipments`: shipper_user_id, origin_city, destination_city, pickup_date, weight_tonnes, goods, vehicle_type, budget_inr, status
  - `requests`: shipper_user_id, origin_city, destination_city, goods, weight_tonnes, vehicle_type, pickup_date, budget_inr, status, created_at, confirmed_at
  - `shipment_requests`: request_id, transporter_user_id, trip_id, price_inr, status, created_at, decided_at
  - `notifications`: user_id, type, title, body, read, created_at
- Severity: **High (integration)** — any drift (renamed/enum/absent columns, RLS denying SELECT/INSERT) breaks the adapter. It is the #1 blocker for Phase “Integration Readiness”.
- Reproduction: set `SUPABASE_URL`+`SUPABASE_ANON_KEY`, call `/market/search/trips` → 500 or empty if columns differ, or RLS denies.
- Fix: verify against the real schema via a read-only contract review (see `LOADSAATHI_INTEGRATION_READINESS.md`) before enabling.

## Risk Area 2 — Automatic selection of Supabase persistence from environment variables

- **Status: CONFIRMED behavior.**
- `get_store()` (database.py:559–567): if `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set → `SupabaseStore`; else SQLite. No explicit store selector.
- Severity: **Medium** — silently switching stores in dev could target the wrong project; with dev-signed JWTs, RLS-denied writes surface as errors (not silent corruption), but confusion is real.
- Reproduction: create `.env` with a Supabase URL/anon key → restart → every marketplace call goes to Supabase.
- Fix: add `DISHA_STORE=demo|supabase` explicit override (default `demo`); warn when env vars are present but store is demo, and vice versa.

## Risk Area 3 — Invalid “confirmed” status assumptions and `confirmed_at`

- **Status: CONFIRMED gap.**
- `SQLiteStore.confirm_request` (database.py:297–305) only checks `status == "pending"` — it does **not** require an accepted offer/precondition. A booking can be confirmed with zero accepted offers.
- Seed data sets `confirmed` + `confirmed_at` on `REQ-HIST1` (a relative day offset) — status semantics are demo-internal.
- `SupabaseStore.confirm_request` (database.py:505) PATCHes `status:"confirmed", confirmed_at: utcnow()` — assumes column exists **and** RLS permits the update.
- Severity: **Medium** (demo integrity; high if mirrored to production without the precondition).
- Reproduction: shipper creates a request, then `confirm request REQ-…` without any offer → request becomes confirmed.
- Fix: (a) require at least one `accepted` offer before confirming; (b) treat `confirmed_at` as write-time only; (c) verify the production lifecycle values during contract review.

## Risk Area 4 — Automatic frontend approvals in portals

- **Status: CONFIRMED.**
- `ShipperPortal.tsx:53,81`, `TruckerPortal.tsx:37,56`, `pages/Shipments.tsx:39,56` call `approve(done.thread_id)` immediately after `chat()` when `approval_required`. No intermediate human confirmation UI is presented in these portal flows (the Chat/Approvals screens still show explicit cards).
- Severity: **Medium (demo UX)** / **Low (security)** — the server-side gate is still enforced (write only occurs via `/approve`), but the “explicit human approval” story is weakened in portal flows.
- Fix: surface `ApprovalCard` and require an explicit button click before calling `approve` in portals (keeps backend gate identical).

## Risk Area 5 — Streaming response mismatch (backend ↔ frontend)

- **Status: CONFIRMED, benign.**
- Backend `/chat` streams ndjson (`main.py:192–207`): `{"type":"chunk","text":…}` then `{"type":"done",…}`.
- Frontend `api.chat()` (`api.ts:110–126`) buffers the full response (`await res.text()`) then parses lines — rendering is animated client-side, not true incremental network streaming.
- Severity: **Low** — functional, but “streaming” is cosmetic; large replies appear after full completion.
- Fix (optional): consume the body as a stream (ReadableStream / fetch reader) for true progressive rendering.

## Risk Area 6 — Actor ownership enforcement on `accept_offer` / `confirm_request`

- **Status: CONFIRMED AUTHORIZATION GAP (High).**
- `SQLiteStore.accept_offer` (database.py:287–295): updates **any** pending offer by id — no check that the caller is the offer's transporter.
- `SQLiteStore.confirm_request` (database.py:297–305): confirms **any** pending request by id — no check that the caller is the request's shipper.
- Tools `_accept_offer` / `_confirm_request` (`tools/marketplace.py:110–121`) likewise perform no ownership check. Only `_make_counter_offer` verifies participation.
- The LangGraph approval gate checks **thread ownership** (service.py:71–73), not resource ownership — so User B can start their own thread, request `confirm request <A's id>`, approve on their own thread, and A's request becomes confirmed.
- Severity: **High** (authorization/integrity in demo; in Supabase mode RLS is the only backstop).
- Reproduction: login as `demo-shipper-02`, chat `confirm request <REQ of shipper-01>`, approve → shipper-01's request flips to `confirmed`.
- Fix: in tools (before store call) resolve the resource and compare `current_user_id()` against `transporter_user_id` (offer) / `shipper_user_id` (request); add tests.

## Risk Area 7 — Approval lifecycle: expiry, exact terms, one-time consumption, revalidation, idempotency

- One-time consumption: **PASS** — after approve/reject, `pending_action` is cleared; duplicate approve → 404 “nothing to approve”.
- Revalidation: **PASS** — `/approve` re-verifies the JWT (service.py:64) and thread owner before resuming.
- Idempotency: **PASS** — retry cannot double-write (state cleared).
- Exact terms: **PASS** — payload executes from checkpoint state; event log records summary.
- Expiry: **FAIL** — pending approvals never expire; an old thread remains approvable indefinitely.
- Severity: **Medium** (operational); recommended: add `approval_expires_at` check in `service.approve` (configurable, e.g., 24 h).

## Risk Area 8 — SQLite persistence & LangGraph checkpoint durability

- **Status: PASS for local demo; caveats for deployment.**
- `SqliteSaver(conn)` on `data/disha.db` (WAL) — verified conversations survive backend restarts.
- Caveats: single-file, single-process assumption; Cloud Run instances have ephemeral disk (checkpoints lost on recycle); concurrent workers share one path.
- Severity: **Low (demo)** / **Medium (deploy)** — for any hosted demo, move checkpoints to the Postgres checkpointer (SQLite stays the local default).

## Risk Area 9 — Matching: ranking-only vs genuine PTL feasibility

- **Status: CONFIRMED ranking-only.**
- `tools/matching.py` normalizes route/capacity/price/date/reliability and ranks; there is no feasibility check (e.g., does the truck actually cover the lane), no partial-truckload (PTL) consolidation, no multi-leg logic.
- Severity: **Low** for the competition (documented limitation); the UI labels scores as “match score”, not feasibility.
- Fix (P2): optional feasibility layer (lane coverage, capacity vs weight/volume, multi-stop) — out of current scope.

## Risk Area 10 — Command Center endpoints authorization

- **Status: PASS.**
- `/market/stats`, `/market/trips`, `/approvals` all require a verified JWT (`Depends(require_user/require_token)`).
- `/approvals` is owner-scoped (service.py:129–153; verified live: shipper1=2, shipper2=0, transporter=0).
- `/market/stats` returns aggregates (not private rows); `/market/trips` lists public demo listings. No private info exposed.
- Verified live: cross-user `/approve` → 403; SQL-injection payload into search → 0 rows (sanitized).

---

## Cross-cutting verified controls

| Control | Where | Status |
|---|---|---|
| No secrets in frontend | frontend/src scan (no console.*, only demo token/mute in localStorage) | PASS |
| Log redaction | `logging_config.py` markers | PASS |
| Caller JWT forwarded to Supabase (anon key only) | `SupabaseStore.__init__` | PASS |
| Service-role key absent from repo | secret scan | PASS |
| Demo-login disabled when Supabase configured / production | `demo_login_enabled` | PASS |
| Production startup fail-closed (issuer/audience/secret required) | `config._production_auth_required` | PASS |

## Test evidence (executed)

```
pytest tests -q  → 73 passed (exit 0)
npm run build     → exit 0
```
