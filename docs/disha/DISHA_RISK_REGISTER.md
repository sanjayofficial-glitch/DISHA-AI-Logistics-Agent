# DISHA Risk Register

**Date:** 2026-11-17 · Status as of the demo build.

| # | Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| 1 | LLM provider rate limits during demo | Medium | Medium | Provider abstraction; Groq fallback; mocked tests; demo planner when no keys | Implemented |
| 2 | Provider outage must not fabricate replies | Medium | High | Failover → clean 503; demo mode ≠ fake success | Implemented + tested |
| 3 | Cross-user data leakage | Low | High | Verified JWT `sub` drives all queries; ownership checks on threads/events/memory/approval | Implemented + tested |
| 4 | Unauthorized writes / auto-confirm | Low | High | `interrupt_before=["execute"]`; approve requires owner; reject writes nothing | Implemented + tested |
| 5 | Prompt injection via marketplace text/memory | Medium | Medium | Retrieved content rendered as data; system prompt forbids obeying embedded instructions | Implemented + tested |
| 6 | Injection in city/id inputs | Low | Medium | Strict sanitization + parameterized queries | Implemented + tested |
| 7 | Secret leakage | Low | High | .env gitignored; no VITE_ keys; no secrets in logs/replies; demo login gated | Implemented |
| 8 | Free-tier ephemeral storage | Medium | Medium | SQLite local-only; deployment guide mandates Postgres checkpointer before going live | Documented |
| 9 | Demo data mistaken for real data | Medium | High | Persistent demo badge; `is_demo`/`source` envelopes; honesty rules | Implemented |
| 10 | Cloud Run surprise billing | Low | High | Budget alert before enabling billing; nothing deployed automatically | Documented |
| 11 | Model name drift | Medium | Low | Model names in `.env` (`GEMINI_MODEL`, `GROQ_MODEL`) | Documented |

## Files that must never change (production safety)

- `supabase/functions/agent-router` and the Freddy agent (not present in this repo —
  if the LoadSaathi repo is mounted here, it must remain untouched).
- LoadSaathi production migrations, RLS policies, Clerk config, Vercel config.
- Anything outside `disha-agent/`, `frontend/`, `docs/disha/`.
