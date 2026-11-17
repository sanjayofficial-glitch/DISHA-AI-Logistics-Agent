# DISHA Deployment Preparation (Phase 6 — readiness only, nothing deployed)

**Status:** plan + verified local runs. Nothing is deployed; deployment happens
only with your explicit action.

## Hosting choices (free/low-cost first)

| Layer | Recommended | Free tier | Persistent storage? |
|---|---|---|---|
| Frontend | Vercel Hobby | Yes | n/a (static + API calls) |
| Backend | Cloud Run (asia-south1) or Render free | Yes (request-based / sleeps idle) | **No** — ephemeral disk |
| DB / checkpoint | Supabase separate demo project (Postgres) | Yes (2 projects, 500 MB) | Yes |
| LLM | Gemini free tier + Groq fallback | Yes (daily limits) | n/a |
| CI | GitHub Actions | Yes | n/a |

Rules from the master spec that must hold before any deploy:
- SQLite must remain the local demo default; any hosted run must move the
  LangGraph checkpointer to Postgres (Supabase) — container disks are ephemeral.
- Set `DISHA_STORE=supabase` only when pointing at a **separate demo project**
  — never production.
- Production fail-closed already requires issuer/audience/JWT secret.

## Required environment (hosted demo)

```
ENVIRONMENT=production
DISHA_STORE=demo            # until the Supabase dry-run passes
GEMINI_API_KEY=             # optional
GROQ_API_KEY=               # optional
SUPABASE_URL=<demo-project> # only when DISHA_STORE=supabase
SUPABASE_ANON_KEY=<demo>
SUPABASE_JWT_SECRET=<demo>
CLERK_EXPECTED_ISSUER=<real>
CLERK_EXPECTED_AUDIENCE=<real>
ALLOWED_ORIGINS=["https://<vercel-app>.vercel.app"]
DB_PATH=/srv/data/disha.db   # local-only (ephemeral on Cloud Run)
APPROVAL_EXPIRES_MINUTES=1440
```

Credentials go into the host's secret manager — never into the repo or
frontend. No real LoadSaathi production keys may be used for demo/prep.

## Budget guardrails (Cloud Run)

- Create a budget alert (low ₹ amount) BEFORE enabling billing.
- Min instances 0; max 2 for the demo; 512Mi memory is enough for this app.
- No cron, no background workers — this is a request-driven API.

## Verification checklist before any deploy

1. [ ] `pytest tests -q` → 91+ pass.
2. [ ] `npm run build` → exit 0.
3. [ ] Supabase dry-run suite (`tests/test_integration_prep.py`) passes against a mock transport.
4. [ ] Fresh demo smoke: login → chat → search → quote → approval flow on the hosted URL.
5. [ ] `/health` reports `demo_mode` correctly for the chosen store.
6. [ ] CORS origin = the actual frontend URL only.

## Rollback

- Cloud Run: redeploy previous revision with `--no-traffic` traffic split.
- Vercel: revert to previous deployment.
- The approval gate + read-only tools mean a misconfigured deploy cannot mutate
  marketplace data by itself.

## Explicit non-goals (this phase)

- No production LoadSaathi connection.
- No migration of production schemas.
- No service-role keys.
- No auto-deploy without approval.
