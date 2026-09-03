"""JSON-file-backed watchlist persistence - same lightweight pattern as
`app.paper_trading.store` (no database; a small per-watchlist file is
sufficient for a single-user research tool and durable across restarts).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

_LOCK = threading.Lock()
_DATA_DIR = Path("data/watchlists")

DEFAULT_WATCHLIST_ID = "default"


def _path(watchlist_id: str) -> Path:
    safe_id = "".join(c for c in watchlist_id if c.isalnum() or c in ("-", "_")) or DEFAULT_WATCHLIST_ID
    return _DATA_DIR / f"{safe_id}.json"


def load_tickers(watchlist_id: str) -> list[str]:
    path = _path(watchlist_id)
    with _LOCK:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []


def save_tickers(watchlist_id: str, tickers: list[str]) -> None:
    path = _path(watchlist_id)
    with _LOCK:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(tickers, indent=2), encoding="utf-8")
