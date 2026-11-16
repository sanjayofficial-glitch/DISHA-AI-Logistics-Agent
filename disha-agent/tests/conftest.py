"""Shared pytest fixtures.

Sets environment before importing the app so the demo store, event store and
LangGraph checkpointer all share one temp database.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="disha_tests_"))
os.environ["ENVIRONMENT"] = "test"
os.environ["DB_PATH"] = str(_TMP / "test.db")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # disha-agent/

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_dev_token  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SQLiteStore  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.cli import seed  # noqa: E402

# Dynamic tables are wiped per test and re-seeded; the static seed tables
# (trips, shipments) stay intact.
RESET_TABLES = [
    "shipment_requests", "requests", "notifications", "facts", "events",
    "checkpoints", "writes", "blobs", "metadata",
]


@pytest.fixture(scope="session", autouse=True)
def _seed_db():
    store = SQLiteStore(settings.db_path)
    seed(store)
    yield store


@pytest.fixture(autouse=True)
def reset_between_tests():
    yield
    import sqlite3
    conn = sqlite3.connect(str(settings.db_path))
    for table in RESET_TABLES:
        try:
            conn.execute(f"DELETE FROM {table}")
        except sqlite3.Error:
            pass
    conn.commit()
    conn.close()
    # Re-seed dynamic rows (requests/offers/notifications) after cleanup
    seed(SQLiteStore(settings.db_path))


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def demo_token(user_id: str = "demo-shipper-01") -> str:
    return create_dev_token(user_id)


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
