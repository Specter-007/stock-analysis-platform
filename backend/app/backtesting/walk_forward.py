"""Walk-forward robustness analysis.

IMPORTANT: the signal engine has no trainable/fitted parameters - it is a
fixed rules-based model. There is therefore no parameter-fitting step on
each fold's "train" window; the train window is shown for reference only
(what history existed before that fold's test window). The actual
simulation for every fold runs the SAME fixed model, via the SAME
`run_backtest` engine used for a single backtest, only on that fold's
"test" window. The purpose is to check whether performance holds up across
several distinct, non-overlapping market periods rather than being an
artifact of one favorable window - never to imply this deterministic model
is being retrained.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd

from app.backtesting.engine import BacktestResult, run_backtest
from app.config import WALK_FORWARD_METHODOLOGY
from app.services.exceptions import InsufficientHistoryError


@dataclass
class WalkForwardFold:
    fold_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    test_total_return_percent: float | None
    test_buy_hold_return_percent: float | None
    test_max_drawdown_percent: float | None
    test_sharpe_ratio: float | None
    test_number_of_trades: int
    test_win_rate_percent: float | None


@dataclass
class WalkForwardResult:
    ticker: str
    train_years: float
    test_years: float
    folds: list[WalkForwardFold] = field(default_factory=list)
    folds_with_positive_return: int = 0
    average_test_return_percent: float | None = None
    methodology: str = WALK_FORWARD_METHODOLOGY


def _add_years(d: dt.date, years: float) -> dt.date:
    return d + dt.timedelta(days=round(years * 365.25))


def run_walk_forward(
    ticker: str,
    full_price_df: pd.DataFrame,
    train_years: float,
    test_years: float,
    max_folds: int,
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
) -> WalkForwardResult:
    if full_price_df.empty:
        return WalkForwardResult(ticker=ticker, train_years=train_years, test_years=test_years)

    data_start = full_price_df.index[0].date()
    data_end = full_price_df.index[-1].date()

    # Generate every possible (train, test) window across the full available
    # history, then keep only the MOST RECENT `max_folds` of them. Iterating
    # forward and stopping at max_folds would otherwise only ever show the
    # oldest folds for a long-listed ticker (e.g. an AAPL walk-forward would
    # never get past the 1980s) and silently omit recent, more relevant
    # market periods.
    all_windows: list[tuple[dt.date, dt.date, dt.date, dt.date]] = []
    cursor = data_start
    while True:
        train_start = cursor
        train_end = _add_years(train_start, train_years)
        test_start = train_end
        test_end = _add_years(test_start, test_years)
        if test_end > data_end:
            break
        all_windows.append((train_start, train_end, test_start, test_end))
        cursor = _add_years(cursor, test_years)

    selected_windows = all_windows[-max_folds:]

    folds: list[WalkForwardFold] = []
    for fold_index, (train_start, train_end, test_start, test_end) in enumerate(selected_windows, start=1):
        try:
            result: BacktestResult = run_backtest(
                ticker=ticker,
                full_price_df=full_price_df,
                start_date=test_start,
                end_date=test_end,
                initial_capital=initial_capital,
                transaction_cost_bps=transaction_cost_bps,
                slippage_bps=slippage_bps,
            )
            folds.append(
                WalkForwardFold(
                    fold_index=fold_index,
                    train_start=str(train_start),
                    train_end=str(train_end),
                    test_start=str(test_start),
                    test_end=str(test_end),
                    test_total_return_percent=result.total_return_percent,
                    test_buy_hold_return_percent=result.buy_hold_return_percent,
                    test_max_drawdown_percent=result.max_drawdown_percent,
                    test_sharpe_ratio=result.sharpe_ratio,
                    test_number_of_trades=result.trade_stats.get("number_of_trades", 0),
                    test_win_rate_percent=result.trade_stats.get("win_rate_percent"),
                )
            )
        except InsufficientHistoryError:
            pass  # not enough data in this fold's test window; skip it, don't fabricate

    returns = [f.test_total_return_percent for f in folds if f.test_total_return_percent is not None]
    avg_return = round(sum(returns) / len(returns), 2) if returns else None
    positive_count = sum(1 for r in returns if r > 0)

    return WalkForwardResult(
        ticker=ticker,
        train_years=train_years,
        test_years=test_years,
        folds=folds,
        folds_with_positive_return=positive_count,
        average_test_return_percent=avg_return,
    )
