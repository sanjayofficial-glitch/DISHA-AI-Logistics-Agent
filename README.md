# DISHA — AI Logistics Agent for LoadSaathi

DISHA is an AI logistics agent built for the Dubai AI Competition. It is a
separate Python + FastAPI + LangGraph backend (`disha-agent/`) plus a React
frontend (`frontend/`) that talks to it. It runs fully in **demo mode** today
(synthetic seed data, deterministic planner, honest labels); real providers
(Gemini/Groq/Supabase) switch on via `.env`.

## Run it (two terminals)

```bash
# 1. Backend — demo mode, no keys needed
cd disha-agent
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# 2. Frontend
cd frontend
npm install
npm run dev          # open http://localhost:5173
```

Sign in with a demo account (Demo Shipper 01 / Demo Transporter 01).

## What's inside

- `disha-agent/` — FastAPI backend, LangGraph workflow with a human approval gate
  before every write, deterministic matching engine (route 35% · capacity 25% ·
  price 20% · date 10% · reliability 10%), per-user memory, events store, tools.
- `frontend/` — Disha chat view (with browser voice), Command Center (live
  pipeline, activity feed, measured metrics), Shipper and Trucker portals.
- `docs/disha/` — architecture, implementation plan, risk register, security,
  test and QA reports, deployment guide, and the competition recording storyboard.

## Key files

- Playbook: `DISHA_Free_Build_Playbook.md`
- Backend README: `disha-agent/README.md`
- Env template: `disha-agent/.env.example`

## Branch rule

All DISHA work happens on `feature/disha-langgraph`. Never develop on `main`.
Production LoadSaathi code is never modified.
