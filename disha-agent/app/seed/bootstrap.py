"""Bootstrap: auto-seed the demo store on startup (demo mode only)."""
from __future__ import annotations

from ..config import settings


def ensure_demo_seeded() -> None:
    if not settings.demo_mode:
        return
    from ..database import SQLiteStore
    from .cli import seed

    store = SQLiteStore(settings.db_path)
    if store._q1("SELECT COUNT(*) c FROM trips")["c"] == 0:
        seed(store)
