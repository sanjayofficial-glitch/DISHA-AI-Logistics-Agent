"""Integration-prep tests — row contracts, dry-run wrapper, store activation guard."""
from __future__ import annotations

import pytest

from app.integration.contract import validate_row, ROW_CONTRACTS
from app.integration.dryrun import DryRunStore
from app.database import SQLiteStore, get_store
from app.config import settings


def test_contract_validates_seeded_rows():
    store = SQLiteStore(settings.db_path)
    trip = store.get_trip("TRIP-0001")
    shipment = store.get_shipment("SHP-0001")
    req = store.get_request("REQ-HIST1")
    offer = store.get_offer("OFF-HIST1")
    assert validate_row("trips", trip)["id"] == "TRIP-0001"
    assert validate_row("shipments", shipment)["id"] == "SHP-0001"
    assert validate_row("requests", req)["status"] == "confirmed"
    assert validate_row("shipment_requests", offer)["status"] == "accepted"


def test_contract_rejects_missing_required_field():
    with pytest.raises(Exception):
        validate_row("trips", {"origin_city": "x"})  # missing id


def test_dryrun_records_and_validates_reads():
    inner = SQLiteStore(settings.db_path)
    dry = DryRunStore(inner)
    trips = dry.get_active_trips()
    assert trips and trips[0]["id"]
    assert any(c["method"] == "get_active_trips" and c["ok"] for c in dry.calls)


def test_dryrun_not_live_by_default():
    inner = SQLiteStore(settings.db_path)
    assert DryRunStore(inner).live_enabled is False


def test_supabase_store_requires_credentials(monkeypatch):
    monkeypatch.setattr(settings, "store", "supabase")
    monkeypatch.setattr(settings, "supabase_url", None)
    monkeypatch.setattr(settings, "supabase_anon_key", None)
    with pytest.raises(ValueError):
        get_store("tok")


def test_contracts_cover_all_adapter_tables():
    assert {"trips", "shipments", "requests", "shipment_requests", "notifications"} <= set(ROW_CONTRACTS)
