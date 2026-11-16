"""Deterministic matching engine tests."""
from app.database import SQLiteStore
from app.tools.matching import rank_candidates, score_candidate
from app.config import settings

INTENT_TRUCK = {
    "origin": "Rourkela",
    "destination": "Ranchi",
    "weight_tonnes": 8,
    "pickup_date": "2026-12-01",
    "budget_inr": 40000,
}


def test_score_factor_weights():
    store = SQLiteStore(settings.db_path)
    rows = store.search_trips("Rourkela", "Ranchi")
    assert rows
    scored = score_candidate(rows[0], INTENT_TRUCK, "find_truck")
    factors = scored["factors"]
    assert set(factors) == {"route", "capacity", "price", "date", "reliability"}
    # weights documented in module
    import app.tools.matching as m
    assert (m.W_ROUTE, m.W_CAPACITY, m.W_PRICE, m.W_DATE, m.W_RELIABILITY) == (0.35, 0.25, 0.20, 0.10, 0.10)
    # total = weighted sum
    total = (
        m.W_ROUTE * factors["route"]["score"]
        + m.W_CAPACITY * factors["capacity"]["score"]
        + m.W_PRICE * factors["price"]["score"]
        + m.W_DATE * factors["date"]["score"]
        + m.W_RELIABILITY * factors["reliability"]["score"]
    )
    assert abs(total - scored["total_score"]) < 1e-6
    assert "Route" in scored["explanation"]
    assert "0.35" in scored["explanation"]


def test_rank_sorted_and_explanations():
    store = SQLiteStore(settings.db_path)
    rows = store.search_trips("Rourkela", "Ranchi")
    ranked = rank_candidates(rows, INTENT_TRUCK, "find_truck")
    scores = [c["total_score"] for c in ranked]
    assert scores == sorted(scores, reverse=True)
    for c in ranked:
        assert c["is_demo"] is True
        assert c["source"] == "synthetic_seed_data"
        assert c["explanation"]


def test_empty_rows_rank_empty():
    assert rank_candidates([], INTENT_TRUCK, "find_truck") == []
