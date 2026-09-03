"""V4 P2.7: model-vs-model (v1.0 vs v1.1) forward comparison.

Runs the SAME backtest engine twice, once per supported model version, over
an identical period - and, if forward paper-trading portfolios are supplied
for each version, reports their real observed sample sizes and returns too.
This never claims one version is "better": with typically small forward
sample sizes, a return difference of a few percentage points is well within
noise, and the methodology string says so explicitly rather than letting a
sorted table imply a verdict it can't support.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from app.backtesting.engine import run_backtest
from app.config import SUPPORTED_MODEL_VERSIONS
from app.paper_trading import forward_validation

MODEL_COMPARISON_METHODOLOGY = (
    "Each model version is run through the exact same backtest engine over the exact same period - "
    "the only thing that differs is which version's scoring/normalization logic evaluated the "
    "signals. This is NOT a claim that one version is statistically superior: forward paper-trading "
    "sample sizes in particular are typically small (see trading_days_observed and "
    "insufficient_sample on each forward row), and a difference of a few percentage points between "
    "versions from a handful of trading days is well within ordinary noise, not evidence of a "
    "better model. Use this to see what changed, not to declare a winner."
)


def compare_model_versions(
    ticker: str,
    full_price_df: pd.DataFrame,
    start_date: dt.date,
    end_date: dt.date,
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
    forward_portfolio_ids: dict[str, str] | None = None,
) -> dict:
    forward_portfolio_ids = forward_portfolio_ids or {}
    backtest_rows = []
    for version in SUPPORTED_MODEL_VERSIONS:
        result = run_backtest(
            ticker=ticker, full_price_df=full_price_df, start_date=start_date, end_date=end_date,
            initial_capital=initial_capital, transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps, model_version=version,
        )
        backtest_rows.append(
            {
                "model_version": version,
                "total_return_percent": result.total_return_percent,
                "cagr_percent": result.advanced_metrics.get("cagr_percent"),
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown_percent": result.max_drawdown_percent,
                "number_of_trades": result.trade_stats.get("number_of_trades", 0),
                "win_rate_percent": result.trade_stats.get("win_rate_percent"),
            }
        )

    forward_rows = []
    for version, portfolio_id in forward_portfolio_ids.items():
        if not portfolio_id:
            continue
        fv = forward_validation.get_forward_validation(portfolio_id)
        forward_rows.append(
            {
                "model_version": version,
                "portfolio_id": portfolio_id,
                "trading_days_observed": fv.trading_days_observed,
                "total_return_percent": fv.total_return_percent,
                "insufficient_sample": fv.insufficient_sample,
            }
        )

    return {
        "ticker": ticker,
        "backtest_comparison": backtest_rows,
        "forward_comparison": forward_rows,
        "methodology": MODEL_COMPARISON_METHODOLOGY,
    }
