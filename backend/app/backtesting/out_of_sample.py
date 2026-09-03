"""In-sample / validation / out-of-sample period splitting.

This reuses the exact same `run_backtest()` engine for all three periods -
there is no separate "training" step because the signal engine has no
fitted parameters. What this guards against is a *human* mistake: eyeballing
a strategy's full-history equity curve, tuning expectations around it, and
then calling the SAME period "confirmation." By forcing three explicit,
chronologically ordered, non-overlapping windows and labeling the last one
unambiguously as OUT_OF_SAMPLE, the UI makes clear which number is the one
that was never looked at while forming an opinion of the strategy.

No additional leakage-prevention logic is needed beyond what the backtest
engine already guarantees: every indicator is causal (see
`backtesting/engine.py` docstring), so a period's signals only ever depend
on data up to and including that period's own dates, regardless of what
other periods are also being evaluated from the same underlying price series.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd

from app.backtesting.engine import BacktestResult, run_backtest
from app.config import MODEL_VERSION_CURRENT
from app.services.exceptions import InsufficientHistoryError

PERIOD_LABELS = ("IN_SAMPLE", "VALIDATION", "OUT_OF_SAMPLE")


@dataclass
class PeriodResult:
    label: str
    start_date: str
    end_date: str
    trading_days: int
    total_return_percent: float | None
    cagr_percent: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    max_drawdown_percent: float | None
    number_of_trades: int
    win_rate_percent: float | None
    buy_hold_return_percent: float | None
    error: str | None = None


@dataclass
class OutOfSampleResult:
    ticker: str
    model_version: str
    periods: list[PeriodResult] = field(default_factory=list)


def _period_from_backtest(label: str, start: dt.date, end: dt.date, result: BacktestResult) -> PeriodResult:
    return PeriodResult(
        label=label,
        start_date=str(start),
        end_date=str(end),
        trading_days=result.trading_days,
        total_return_percent=result.total_return_percent,
        cagr_percent=result.advanced_metrics.get("cagr_percent"),
        sharpe_ratio=result.sharpe_ratio,
        sortino_ratio=result.advanced_metrics.get("sortino_ratio"),
        max_drawdown_percent=result.max_drawdown_percent,
        number_of_trades=result.trade_stats.get("number_of_trades", 0),
        win_rate_percent=result.trade_stats.get("win_rate_percent"),
        buy_hold_return_percent=result.buy_hold_return_percent,
    )


def run_out_of_sample_validation(
    ticker: str,
    full_price_df: pd.DataFrame,
    windows: list[tuple[str, dt.date, dt.date]],
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
    model_version: str = MODEL_VERSION_CURRENT,
) -> OutOfSampleResult:
    """`windows` is a list of (label, start, end) tuples, expected to already
    be chronologically ordered and non-overlapping (validated by the caller /
    request schema).
    """
    periods: list[PeriodResult] = []

    for label, start, end in windows:
        try:
            result = run_backtest(
                ticker=ticker,
                full_price_df=full_price_df,
                start_date=start,
                end_date=end,
                initial_capital=initial_capital,
                transaction_cost_bps=transaction_cost_bps,
                slippage_bps=slippage_bps,
                model_version=model_version,
            )
            periods.append(_period_from_backtest(label, start, end, result))
        except InsufficientHistoryError as exc:
            periods.append(
                PeriodResult(
                    label=label,
                    start_date=str(start),
                    end_date=str(end),
                    trading_days=0,
                    total_return_percent=None,
                    cagr_percent=None,
                    sharpe_ratio=None,
                    sortino_ratio=None,
                    max_drawdown_percent=None,
                    number_of_trades=0,
                    win_rate_percent=None,
                    buy_hold_return_percent=None,
                    error=str(exc),
                )
            )

    return OutOfSampleResult(ticker=ticker, model_version=model_version, periods=periods)
