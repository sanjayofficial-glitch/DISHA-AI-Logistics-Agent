# DISHA Task Plan — P0 / P1 / P2

**Source of truth:** `IMPLEMENTATION_BASELINE.md` + `SECURITY_AND_DATA_SAFETY_AUDIT.md` (17 Nov 2026).
**Rule:** no production LoadSaathi access, no deployments, no merges without approval; every change lands on a dedicated branch with tests; all writes remain approval-gated.

---

## P0 — must do before the competition demo

| # | Task | Ref | Severity | Done when |
|---|---|---|---|---|
| P0-1 | **Enforce resource ownership in `accept_offer` / `confirm_request`** — in `app/tools/marketplace.py` `_accept_offer`/`_confirm_request`, resolve the row and compare `current_user_id()` with `transporter_user_id` (offer) / `shipper_user_id` (request); reject otherwise. Add tests (cross-user accept/confirm → 403/error). | Audit RA6 | High | pytest green incl. new tests |
| P0-2 | **Explicit store selector + warning** — add `DISHA_STORE=demo|supabase` in `config.py`, default `demo`; `get_store()` honors it; warn when env vars and selector disagree. | Audit RA2 | Medium | config tests + startup log |
| P0-3 | **Confirm-request precondition** — `confirm_request` requires ≥1 `accepted` offer on the request (else honest error). Keeps “confirmed” meaningful. | Audit RA3 | Medium | pytest new test |
| P0-4 | **Portals: explicit approval UI** — replace auto-`approve()` in ShipperPortal/TruckerPortal/Shipments with a visible `ApprovalCard` requiring a click. Backend gate unchanged. | Audit RA4 | Medium | manual smoke + typecheck |
| P0-5 | **Approval expiry** — `approval_expires_at` (default 24 h) checked in `service.approve`/`reject`; expired → clear and 410/404. | Audit RA7 | Medium | pytest new test |
| P0-6 | **Push `feature/disha-command-center`** + CI green. | Baseline | — | CI success on GitHub |

## P1 — before any hosted/live deployment

| # | Task | Ref | Done when |
|---|---|---|---|
| P1-1 | **Supabase contract verification (read-only)** — produce/confirm a field-level contract (tables, columns, enums, RLS) from the LoadSaathi schema docs; align `SupabaseStore` queries; add a `DISHA_STORE=supabase` dry-run test with a separate Supabase demo project (never production). | RA1/RA2 | contract doc + dry-run green |
| P1-2 | **Move checkpoints to Postgres-aware checkpointer** when hosting on Cloud Run (SQLite stays local demo default). | RA8 | deploy smoke |
| P1-3 | **True incremental streaming** in `api.chat()` via fetch reader (optional UX). | RA5 | typecheck + build |
| P1-4 | **Frontend route-level tests** (happy path per page using the API client against test server). | — | npm test green |
| P1-5 | **Rate-limit + security headers** for any hosted instance (CORS origins tightened; HSTS). | — | security re-audit |

## P2 — post-competition / product growth

| # | Task | Ref | Notes |
|---|---|---|---|
| P2-1 | Feasibility/PTL layer in matching (lane coverage, volume vs weight, multi-leg). | RA9 | keep “match score” label |
| P2-2 | Counter-offer acceptance/decline lifecycle UI + status transitions. | RA6/7 | negotiate full lifecycle |
| P2-3 | Multilingual intent (Hindi/Hinglish) model improvements in `DemoProvider`/LLM prompts. | — | Phase 2 stream |
| P2-4 | Notifications for real events (Resend free tier) behind approval gate. | — | separate integration |
| P2-5 | Production deployment hardening (budget alerts, Secret Manager, observability). | RA8 | before any paid hosting |

## Verification for each task

- Backend: `pytest tests -q` (must stay ≥ baseline; new tests for each change).
- Frontend: `npm run build` (tsc --noEmit + vite).
- Repo hygiene: `git diff --check`, secret scan, no parent-repo changes.
- Process: dedicated branch → local commit → review → push only after explicit approval; never merge without approval; never deploy.
