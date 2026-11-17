# LoadSaathi Integration Readiness (DISHA)

**Purpose:** document what is required before DISHA can safely connect to LoadSaathi **through a secure API**, while DISHA remains a separate application (own repo, backend, persistence).

**Current truth:** DISHA runs fully isolated on SQLite demo data. The Supabase adapter exists but is inactive (no env vars set) and its schema assumptions are unverified (see audit RA1).

---

## 1. Architecture boundary (non-negotiable)

- DISHA and LoadSaathi remain **separate repositories/domains**.
- Only two integration surfaces are allowed:
  1. **HTTP API** from DISHA backend to Supabase **PostgREST** (with the caller's Clerk→Supabase JWT + anon key). No direct DB connection, no service-role key, no shared secrets in code.
  2. **Frontend → DISHA backend** (already how the UI works).
- DISHA never touches LoadSaathi's deployment config, workflows, or production DB.

## 2. Authentication contract (must be verified)

| Item | Requirement | Status |
|---|---|---|
| Clerk → Supabase JWT template | Must exist and produce HS256 JWTs with `role=authenticated`, `sub`, issuer, audience | ASSUMED (CODE) |
| Expected issuer/audience | `CLERK_EXPECTED_ISSUER` / `CLERK_EXPECTED_AUDIENCE` set in DISHA env | REQUIRED at deploy |
| JWT secret | `SUPABASE_JWT_SECRET` set in DISHA env (production fail-closed already enforced) | REQUIRED at deploy |
| RLS | Every table access governed by RLS on `auth.uid()` / roles | MUST VERIFY |

## 3. Data contract (must be verified before enabling SupabaseStore)

Tables/columns currently assumed (database.py `SupabaseStore`): `trips`, `shipments`, `requests`, `shipment_requests`, `notifications` — with the column lists in the baseline doc.

**Blocking questions for a read-only contract review:**
1. Exact table/column names and types (including `status` enums, `created_at`/`confirmed_at`/`decided_at`).
2. Which status values are valid (`pending/confirmed/accepted/declined/active/…`).
3. RLS: is `requests.shipper_user_id = auth.uid()` enforced for SELECT/INSERT/UPDATE? Same for `shipment_requests.transporter_user_id` and `notifications.user_id`.
4. Are `INSERT`s allowed with client-generated ids, or should DISHA `omit` id and read it back?
5. Are there triggers (e.g., notifications on insert) that DISHA would duplicate?
6. Timezone expectations (UTC vs IST).

## 4. Read-only first (integration staging)

| Stage | Action | Gate |
|---|---|---|
| 0 | Contract review (above) yields a JSON schema doc | doc approved |
| 1 | Create a **separate Supabase demo project** mirroring the schema with synthetic data | project exists |
| 2 | Run DISHA with `DISHA_STORE=supabase` + demo project env (never production) | dry-run tests green |
| 3 | Enable read-only calls only (search/stats/quote) in the UI for demo | manual demo |
| 4 | Enable approval-gated writes to the demo project only | approval-gate tests green |
| 5 | (Later, with explicit approval) supervised read-only against a LoadSaathi non-production copy | change control sign-off |

## 5. Write-safety guarantees to preserve

- Every write goes through the LangGraph `interrupt_before=["execute"]` approval gate.
- Ownership checks (P0-1) must be in place before any live write path.
- No service-role key; no bulk mutations; no DDL/migrations ever from DISHA.
- All demo endpoints return `is_demo`/`source` markers; never silently mixed with real data.

## 6. Deliverables for this phase

- `LOADSAATHI_SCHEMA_CONTRACT.md` (draft after read-only review).
- A mock/test harness for `SupabaseStore` with a demo project (`tests/test_supabase_contract.py` — skipped by default).
- Environment checklist per environment (dev/demo/production) with required/forbidden variables.

## 7. Explicit non-goals (this phase)

- No connection to production LoadSaathi Supabase.
- No schema changes/migrations to any LoadSaathi database.
- No deployment of DISHA to shared hosting.
- No use of real user data.
