# DISHA agent — Python + FastAPI + LangGraph backend

AI logistics agent for the LoadSaathi platform (Dubai AI Competition demo).

## Run locally (demo mode — no keys required)

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Demo mode auto-seeds a synthetic marketplace (trips, shipments, requests, offers,
notifications). `GET http://127.0.0.1:8000/health` reports `demo_mode: true`.

## Switch on live providers

Copy `.env.example` → `.env` and fill:

| Env | Purpose |
|---|---|
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Primary LLM (REST) |
| `GROQ_API_KEY` / `GROQ_MODEL` | Fallback LLM (OpenAI-compatible) |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | Real marketplace tables (anon key + caller JWT) |
| `SUPABASE_JWT_SECRET` | JWT signing/verification — **highly sensitive**; setting it disables demo login |
| `CLERK_EXPECTED_ISSUER` / `CLERK_EXPECTED_AUDIENCE` | Clerk→Supabase JWT contract |

With a real key configured, provider failures surface as honest errors — never
fake replies. With no keys, the deterministic (explicitly labeled) demo planner is
used.

## Tests

```bash
.venv\Scripts\python -m pytest tests -q   # 39 tests
```

## Notable design points

- **Approval gate:** the LangGraph workflow compiles with `interrupt_before=["execute"]`;
  every marketplace write requires `POST /approve`. The JWT is request-scoped and
  never persisted to checkpoints.
- **Matching engine:** deterministic, per-factor explanations (route 35% /
  capacity 25% / price 20% / date 10% / reliability 10%).
- **Memory:** per-user facts (SQLite) with strict isolation; only explicit
  "remember that …" writes.
- **Events store:** every node transition is recorded and powers the Command Center
  and measured metrics.
- **Migration path:** `MarketplaceStore` (SQLite ↔ Supabase) swap is a `.env` change;
  the checkpointer can move to Postgres for deployment (see
  `../docs/disha/DISHA_DEPLOYMENT_GUIDE.md`).
