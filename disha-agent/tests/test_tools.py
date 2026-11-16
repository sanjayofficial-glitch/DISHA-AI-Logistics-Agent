"""Tool layer + injection-resistance tests."""
from __future__ import annotations

from app.database import SQLiteStore
from app.tools.marketplace import clean_city
from app.tools.registry import get_tool, list_tools
from app.config import settings


def test_tool_registry_has_readonly_write_tools():
    names = {t.name for t in list_tools()}
    assert names >= {"search_trips", "search_shipments", "get_market_stats",
                     "create_shipment_request", "create_transporter_offer",
                     "accept_offer", "confirm_request", "send_notification"}


def test_search_trips_injection_attempt_safe():
    store = SQLiteStore(settings.db_path)
    tool = get_tool("search_trips")
    result = tool.run(store, {"origin": "Rourkela' OR 1=1 --", "destination": "Ranchi"})
    assert result.ok is True
    # The attempt must not return unrelated rows — cleaned city yields empty set.
    assert result.data["count"] == 0


def test_search_trips_sql_comment_attempt_safe():
    store = SQLiteStore(settings.db_path)
    tool = get_tool("search_trips")
    result = tool.run(store, {"origin": "Rourkela; DROP TABLE trips;", "destination": "Ranchi"})
    assert result.ok is True
    assert result.data["count"] == 0


def test_create_request_validates_payload():
    store = SQLiteStore(settings.db_path)
    tool = get_tool("create_shipment_request")
    result = tool.run(store, {"origin": "", "destination": "", "weight_tonnes": -5})
    assert result.ok is False
    assert result.error


def test_clean_city_strips_control_chars():
    assert clean_city("Rourkela' OR 1=1 --") == "rourkela or 11"
    assert clean_city("  Ranchi  ") == "ranchi"
    assert clean_city(None) == ""
    assert clean_city("Rourkela; DROP TABLE trips;") == "rourkela drop table trips"
