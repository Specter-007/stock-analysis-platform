"""Historical signal-performance analytics.

Answers "historically, what happened in the N sessions AFTER this model
produced a BUY (or SELL) signal for this ticker?" using only data that has
already occurred - this is retrospective descriptive statistics over the
past, not a forecast, and is clearly distinguished from prediction in every
label surfaced to the user. It is deliberately NOT framed as an "accuracy"
percentage, which would misleadingly imply the model is a predictor.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

import pandas as pd

from app.config import (
    MODEL_VERSION_CURRENT,
    SIGNAL_PERFORMANCE_HORIZONS_SESSIONS,
    SIGNAL_PERFORMANCE_LOOKBACK_SESSIONS,
)
from app.indicators.compute import safe_float
from app.signals.engine import SignalResult
from app.signals.history import compute_signal_history_full


@dataclass
class HorizonStats:
    horizon_sessions: int
    sample_size: int
    positive_rate_percent: float | None
    average_return_percent: float | None
    median_return_percent: float | None


@dataclass
class SignalPerformanceGroup:
    signal_group: str  # "BUY" (BUY+STRONG_BUY) | "SELL" (SELL+STRONG_SELL)
    total_signals: int
    horizons: list[HorizonStats] = field(default_factory=list)


def _forward_return_pct(close: pd.Series, date_position: int, horizon: int) -> float | None:
    target_idx = date_position + horizon
    if target_idx >= len(close):
        return None
    base = safe_float(close.iloc[date_position])
    future = safe_float(close.iloc[target_idx])
    if base is None or future is None or base == 0:
        return None
    return (future / base - 1.0) * 100.0


def _group_stats(
    signal_group: str,
    matching_dates: list[str],
    close: pd.Series,
    horizons: tuple[int, ...],
) -> SignalPerformanceGroup:
    # `close.index` is timezone-aware (from yfinance); matching plain "YYYY-MM-DD"
    # date strings against it via get_indexer/get_loc silently fails (returns -1)
    # because of the naive-vs-aware mismatch. Build a plain-date -> integer
    # position map once, up front, and look up everything through that instead.
    date_to_position = {ts.date(): i for i, ts in enumerate(close.index)}
    matching_positions = [
        date_to_position[pd.Timestamp(d).date()]
        for d in matching_dates
        if pd.Timestamp(d).date() in date_to_position
    ]

    horizon_stats = []
    for h in horizons:
        returns = []
        for pos in matching_positions:
            r = _forward_return_pct(close, pos, h)
            if r is not None:
                returns.append(r)

        if returns:
            positive_rate = round(sum(1 for r in returns if r > 0) / len(returns) * 100, 1)
            avg = round(statistics.mean(returns), 2)
            median = round(statistics.median(returns), 2)
        else:
            positive_rate = avg = median = None

        horizon_stats.append(
            HorizonStats(
                horizon_sessions=h,
                sample_size=len(returns),
                positive_rate_percent=positive_rate,
                average_return_percent=avg,
                median_return_percent=median,
            )
        )

    return SignalPerformanceGroup(
        signal_group=signal_group,
        total_signals=len(matching_dates),
        horizons=horizon_stats,
    )


def compute_signal_performance(
    indicator_df: pd.DataFrame,
    lookback_sessions: int = SIGNAL_PERFORMANCE_LOOKBACK_SESSIONS,
    horizons: tuple[int, ...] = SIGNAL_PERFORMANCE_HORIZONS_SESSIONS,
    model_version: str = MODEL_VERSION_CURRENT,
) -> list[SignalPerformanceGroup]:
    full_history = compute_signal_history_full(indicator_df, lookback_sessions, model_version)
    close = indicator_df["Close"]

    buy_dates = [d for d, r in full_history if r.signal in ("BUY", "STRONG_BUY")]
    sell_dates = [d for d, r in full_history if r.signal in ("SELL", "STRONG_SELL")]

    return [
        _group_stats("BUY", buy_dates, close, horizons),
        _group_stats("SELL", sell_dates, close, horizons),
    ]
