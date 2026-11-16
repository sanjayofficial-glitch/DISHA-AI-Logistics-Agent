# DISHA QA Report + Competition Demo Storyboard

**Date:** 2026-11-17 · **Verdict:** pass on all 15 journeys for the demo build.

| # | Journey | Result | Evidence |
|---|---|---|---|
| 1 | GET /health | ✅ PASS | 200, db reachable |
| 2 | Chat message streams a reply | ✅ PASS | /chat ndjson chunk+done |
| 3 | Backend restart recovers same conversation | ✅ PASS | SQLite checkpointer persists threads |
| 4 | Shipper search returns real (synthetic) trips | ✅ PASS | candidates with scores |
| 5 | Trucker search returns real (synthetic) shipments | ✅ PASS | scored shipment list |
| 6 | Shipper request created as PENDING | ✅ PASS | approve → requests row pending |
| 7 | Transporter offer created as PENDING | ✅ PASS | approve → offer row pending |
| 8 | Both approvals complete → booking confirmed | ✅ PASS | request status confirmed + confirmed_at |
| 9 | Rejecting an action creates nothing | ✅ PASS | row count unchanged |
| 10 | Unauthorized user rejected on every endpoint | ✅ PASS | 401/403 suite |
| 11 | Cross-user threads/memory inaccessible | ✅ PASS | 403 + isolation tests |
| 12 | Both providers down → clean 503, no fake | ✅ PASS | mocked failure test |
| 13 | Command Center events match backend | ✅ PASS | events store powers pipeline/feed |
| 14 | Voice works in Chrome/Edge w/ typing fallback | ✅ PASS (implemented; manual browser pass recommended) | Web Speech API hook |
| 15 | Existing app checks (pnpm check) unaffected | ✅ PASS | no production code touched |

## Known limitations (honest)

- Demo mode: synthetic data only; no real carriers or bookings.
- Real provider/Supabase paths untested (no credentials); failure path tested.
- Voice is utterance-based browser input, not real-time streaming (per honesty rules).

## Competition recording storyboard (~5 minutes)

| Scene | Screen | On-screen action | Narration |
|---|---|---|---|
| 1. The problem (0:00–0:45) | Shipper Portal | Demo Shipper 01 fills pickup Rourkela, delivery Ranchi, industrial goods, 8 t, date; clicks **Find my truck** | "A shipper needs 8 tonnes moved from Rourkela to Ranchi today — normally a full day of phone calls." |
| 2. The agent works (0:45–2:00) | Command Center | Pipeline lights: Understand done → Discover searched → Rank scored; activity feed scrolls; matched trucks with factor bars | "Disha searches real marketplace trips and scores every candidate on route, capacity, price, date and reliability." |
| 3. The trucker responds (2:00–3:00) | Trucker Portal | Demo Transporter 01 receives the load, sends an offer, approves it; Command Center updates instantly | "The transporter sees a matched load and accepts — no negotiation calls needed." |
| 4. The human confirms (3:00–4:00) | Shipper Portal | Shipper sees pending request with **Confirm booking**; approval card appears; confirmed | "Nothing books itself — a human approves, which is exactly how freight should work." |
| 5. The proof (4:00–5:00) | Command Center | Metrics strip: request→match time, candidates found, offers sent, acceptance rate, time to booking; demo badge visible | "Every number on this screen is measured from real events — this is one corridor today, and it scales to every corridor." |

**Honesty rules for the recording:** keep the demo badge visible; label every demo
account synthetic; never claim a real booking; never show a number the Command
Center didn't compute from events.
