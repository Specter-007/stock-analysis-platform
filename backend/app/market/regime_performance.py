"""Connects market-regime detection to actual realized strategy performance.

Methodology: for every trading day in the backtest period, the BENCHMARK's
regime is classified causally (using only data through that day - identical
to `market.regime.classify_market_regime`). The strategy's own daily returns
are then grouped by which regime was active that day, and compounded within
each bucket. This answers "how did this strategy actually do on days the
market was classified Bull/Bear/Sideways/High-Volatility?" - not a
simulation, a regrouping of the SAME realized backtest returns.

Trades are bucketed by the regime active on their ENTRY date, since that is
the date the strategy's decision was actually made.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.backtesting import metrics as m
from app.backtesting.engine import BacktestResult
from app.indicators.compute import compute_indicator_frame
from app.market.regime import classify_market_regime

REGIME_ORDER = ("BULL", "BEAR", "SIDEWAYS", "HIGH_VOLATILITY", "UNAVAILABLE")


@dataclass
class RegimeBucketResult:
    regime: str
    trading_days: int
    frequency_percent: float
    compounded_return_percent: float | None
    annualized_volatility_percent: float | None
    sharpe_ratio: float | None
    number_of_trades: int
    win_rate_percent: float | None


@dataclass
class RegimePerformanceResult:
    ticker: str
    benchmark: str
    buckets: list[RegimeBucketResult] = field(default_factory=list)
    methodology: str = (
        "Each trading day's benchmark regime is classified causally (using only data through "
        "that day). The strategy's realized daily returns are grouped by the regime active that "
        "day and compounded within each group. Trades are bucketed by the regime active on their "
        "entry date. This regroups the SAME backtest that already ran - it is not a separate "
        "simulation for each regime."
    )


def _classify_regime_by_date(benchmark: str, benchmark_full_price_df: pd.DataFrame, dates: pd.DatetimeIndex) -> dict:
    """Returns {plain python date -> regime label}.

    `benchmark_full_price_df.index` is timezone-aware (from yfinance); the
    backtest's own date strings are plain "YYYY-MM-DD" (timezone-naive).
    Comparing/slicing a tz-aware DatetimeIndex against naive Timestamps
    raises TypeError - so lookups go through a plain-`date()` position map
    instead of `.loc[:timestamp]` slicing (same pattern used in
    `signals/performance.py` for the identical underlying tz mismatch).
    """
    indicator_df = compute_indicator_frame(benchmark_full_price_df)
    date_to_position = {ts.date(): i for i, ts in enumerate(indicator_df.index)}

    result_by_date = {}
    for date in dates:
        plain_date = date.date() if hasattr(date, "date") else date
        pos = date_to_position.get(plain_date)
        if pos is None:
            result_by_date[plain_date] = "UNAVAILABLE"
            continue
        sliced = indicator_df.iloc[: pos + 1]
        result_by_date[plain_date] = classify_market_regime(benchmark, sliced).regime
    return result_by_date


def compute_regime_performance(
    ticker: str,
    benchmark: str,
    backtest_result: BacktestResult,
    benchmark_full_price_df: pd.DataFrame,
) -> RegimePerformanceResult:
    strategy_dates = [pd.Timestamp(p.date).date() for p in backtest_result.strategy_curve]
    equity = pd.Series([p.equity for p in backtest_result.strategy_curve], index=strategy_dates)
    daily_returns = equity.pct_change()

    strategy_dates_ts = pd.DatetimeIndex([pd.Timestamp(d) for d in strategy_dates])
    regime_by_date = _classify_regime_by_date(benchmark, benchmark_full_price_df, strategy_dates_ts)
    regime_series = pd.Series(regime_by_date)

    total_days = len(strategy_dates)
    buckets: list[RegimeBucketResult] = []

    trade_entry_regimes = []
    for t in backtest_result.trades:
        entry_date = pd.Timestamp(t.entry_date).date()
        regime = regime_by_date.get(entry_date)
        if regime is None:
            # fall back to nearest available date on/after entry
            candidates = [d for d in strategy_dates if d >= entry_date]
            regime = regime_by_date.get(candidates[0]) if candidates else "UNAVAILABLE"
        trade_entry_regimes.append((regime, t))

    for regime in REGIME_ORDER:
        regime_dates = regime_series[regime_series == regime].index
        if len(regime_dates) == 0:
            continue

        regime_returns = daily_returns.reindex(regime_dates).dropna()
        compounded = (
            round((float(np.prod(1.0 + regime_returns.to_numpy())) - 1.0) * 100.0, 2)
            if len(regime_returns) > 0
            else None
        )
        vol = m.annualized_volatility_percent(regime_returns) if len(regime_returns) > 1 else None
        sharpe = m.sharpe_ratio(regime_returns) if len(regime_returns) > 1 else None

        regime_trades = [t for r, t in trade_entry_regimes if r == regime]
        closed = [t for t in regime_trades if t.pnl is not None]
        win_rate = round(len([t for t in closed if t.pnl > 0]) / len(closed) * 100, 1) if closed else None

        buckets.append(
            RegimeBucketResult(
                regime=regime,
                trading_days=len(regime_dates),
                frequency_percent=round(len(regime_dates) / total_days * 100, 1) if total_days else 0.0,
                compounded_return_percent=compounded,
                annualized_volatility_percent=vol,
                sharpe_ratio=round(sharpe, 3) if sharpe is not None else None,
                number_of_trades=len(regime_trades),
                win_rate_percent=win_rate,
            )
        )

    return RegimePerformanceResult(ticker=ticker, benchmark=benchmark, buckets=buckets)
