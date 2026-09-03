"""Simple JSON-file-backed persistence for paper-trading portfolios.

Deliberately not a database: this is a single-process simulation feature,
not a multi-user brokerage. A small JSON file per portfolio is durable
across backend restarts without introducing any new infrastructure.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from app.config import PAPER_TRADING_DATA_DIR, PAPER_TRADING_DEFAULT_CAPITAL

_LOCK = threading.Lock()

# Resolved relative to the backend/ working directory the app is run from.
_DATA_DIR = Path(PAPER_TRADING_DATA_DIR)


def _portfolio_path(portfolio_id: str) -> Path:
    safe_id = "".join(c for c in portfolio_id if c.isalnum() or c in ("-", "_")) or "default"
    return _DATA_DIR / f"{safe_id}.json"


def _default_state(portfolio_id: str) -> dict:
    return {
        "portfolio_id": portfolio_id,
        "starting_capital": PAPER_TRADING_DEFAULT_CAPITAL,
        "cash": PAPER_TRADING_DEFAULT_CAPITAL,
        "positions": {},  # ticker -> {"shares": float, "avg_entry_price": float}
        "trades": [],  # list of trade dicts, oldest first
        # Append-only forward-validation equity curve - one entry per real
        # trading day the portfolio was actually observed on, never one per
        # calendar day (weekends/holidays are never fabricated). See
        # app.paper_trading.service._maybe_record_snapshot.
        "equity_snapshots": [],
        # Fixes the SPY price/date the benchmark curve is indexed from - set
        # once, on this portfolio's first-ever snapshot, so "started with the
        # same capital on the same day" holds for the life of the portfolio.
        "benchmark_basis": None,
    }


def load_portfolio(portfolio_id: str) -> dict:
    path = _portfolio_path(portfolio_id)
    with _LOCK:
        if not path.exists():
            return _default_state(portfolio_id)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return _default_state(portfolio_id)


def save_portfolio(portfolio_id: str, state: dict) -> None:
    path = _portfolio_path(portfolio_id)
    with _LOCK:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def reset_portfolio(portfolio_id: str, starting_capital: float | None = None) -> dict:
    state = _default_state(portfolio_id)
    if starting_capital is not None:
        state["starting_capital"] = starting_capital
        state["cash"] = starting_capital
    save_portfolio(portfolio_id, state)
    return state
