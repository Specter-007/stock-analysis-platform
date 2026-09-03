"""Watchlist: add/remove real tickers, then enrich each with its actual
current quote and the same deterministic signal engine used everywhere
else in the app - never a cached or fabricated snapshot invented for the
list view.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.indicators.compute import compute_indicator_frame
from app.market.regime import classify_market_regime
from app.services import market_data
from app.signals import engine as signal_engine
from app.signals.history import compute_signal_history
from app.utils.validation import normalize_and_validate_ticker
from app.watchlist.store import DEFAULT_WATCHLIST_ID, load_tickers, save_tickers

logger = logging.getLogger(__name__)

MAX_WATCHLIST_SIZE = 50


class WatchlistError(ValueError):
    pass


@dataclass
class WatchlistEntry:
    ticker: str
    company_name: str | None
    price: float | None
    change_percent: float | None
    signal: str | None
    score: float | None
    trend_classification: str | None
    market_regime: str | None
    data_status: str
    signal_changed_today: bool
    error: str | None = None


@dataclass
class WatchlistResult:
    watchlist_id: str
    tickers: list[str]
    entries: list[WatchlistEntry] = field(default_factory=list)


def add_ticker(watchlist_id: str, ticker: str) -> list[str]:
    ticker = normalize_and_validate_ticker(ticker)
    tickers = load_tickers(watchlist_id)
    if ticker in tickers:
        return tickers
    if len(tickers) >= MAX_WATCHLIST_SIZE:
        raise WatchlistError(f"Watchlist is at its maximum size ({MAX_WATCHLIST_SIZE} tickers).")
    tickers.append(ticker)
    save_tickers(watchlist_id, tickers)
    return tickers


def remove_ticker(watchlist_id: str, ticker: str) -> list[str]:
    ticker = normalize_and_validate_ticker(ticker)
    tickers = [t for t in load_tickers(watchlist_id) if t != ticker]
    save_tickers(watchlist_id, tickers)
    return tickers


def _enrich(ticker: str, regime: str | None) -> WatchlistEntry:
    try:
        overview, meta = market_data.get_overview(ticker)
        full_df, _ = market_data.get_full_daily_history(ticker)

        signal = score = trend = None
        signal_changed = False
        if len(full_df) >= 20:
            indicator_df = compute_indicator_frame(full_df)
            result = signal_engine.evaluate(indicator_df)
            signal, score, trend = result.signal, result.score, result.trend_classification

            history = compute_signal_history(indicator_df, lookback_sessions=2)
            if len(history) >= 2:
                signal_changed = history[-1].signal != history[-2].signal

        return WatchlistEntry(
            ticker=ticker,
            company_name=overview.get("company_name"),
            price=overview.get("last_price"),
            change_percent=overview.get("change_percent"),
            signal=signal,
            score=score,
            trend_classification=trend,
            market_regime=regime,
            data_status=meta.data_status,
            signal_changed_today=signal_changed,
        )
    except Exception as exc:
        logger.warning("Failed to enrich watchlist entry for %s: %s", ticker, exc)
        return WatchlistEntry(
            ticker=ticker,
            company_name=None,
            price=None,
            change_percent=None,
            signal=None,
            score=None,
            trend_classification=None,
            market_regime=None,
            data_status="UNAVAILABLE",
            signal_changed_today=False,
            error="Data temporarily unavailable for this ticker.",
        )


def get_watchlist(watchlist_id: str = DEFAULT_WATCHLIST_ID) -> WatchlistResult:
    tickers = load_tickers(watchlist_id)
    if not tickers:
        return WatchlistResult(watchlist_id=watchlist_id, tickers=[], entries=[])

    try:
        bench_df, _ = market_data.get_full_daily_history("SPY")
        regime = classify_market_regime("SPY", compute_indicator_frame(bench_df)).regime
    except Exception:
        regime = None

    with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as pool:
        entries = list(pool.map(lambda t: _enrich(t, regime), tickers))

    return WatchlistResult(watchlist_id=watchlist_id, tickers=tickers, entries=entries)
