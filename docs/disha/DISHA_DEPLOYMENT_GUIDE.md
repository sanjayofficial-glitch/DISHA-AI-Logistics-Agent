# DISHA Deployment Guide (free tiers — plan only, nothing deployed)

**Status:** configuration + plan ready. **Nothing has been deployed.** Deployment
only happens with your explicit action.

## Backend → Google Cloud Run

1. `docker build -t disha-agent disha-agent/` (slim image, `uvicorn` honours `PORT`).
2. `gcloud run deploy disha-agent --region asia-south1 --min-instances 0 --max-instances 2 --memory 512Mi --allow-unauthenticated=false`
3. Environment (via Secret Manager for secrets):
   - `GEMINI_API_KEY`, `GROQ_API_KEY` (optional)
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`
   - `SUPABASE_JWT_SECRET` — **highly sensitive: it can sign JWTs**. Guard it.
   - `CLERK_EXPECTED_ISSUER`, `CLERK_EXPECTED_AUDIENCE`
   - `ALLOWED_ORIGINS` = the production frontend origin
   - `ENVIRONMENT=production`
4. **Cost guardrails:** a billing account is required; usage beyond the free
   allowance is billed. Create a budget alert (e.g. ₹100) **before** enabling
   billing. Min instances 0 keeps idle cost at zero.
5. **Persistence:** container filesystems are ephemeral. Before any real deploy,
   switch the LangGraph checkpointer to the Postgres checkpointer and point
   `SUPABASE_URL` at the Postgres database. SQLite stays local-only.

## Frontend → Vercel (existing Hobby project)

1. `cd frontend && npm run build` → `dist/`.
2. Add `VITE_DISHA_API_URL=https://<cloud-run-url>` to the Vercel project env.
3. Update backend `ALLOWED_ORIGINS` to the Vercel production origin.

## Rollback

- Cloud Run: redeploy the previous image revision (`gcloud run revisions list` +
  `--no-traffic`/traffic split).
- Vercel: revert to previous deployment from the project dashboard.
- The approval gate + read-only tools mean a misconfigured deploy cannot mutate
  marketplace data by itself.

## Demo-first reminder

The competition demo runs entirely locally (uvicorn + Vite). Deployment is an
optional URL for judges; the recorded video never depends on hosting.
