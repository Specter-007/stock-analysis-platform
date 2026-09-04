"""V5: transaction-cost and slippage stress testing.

Reuses `run_backtest` completely unchanged. Trade decisions never depend on
cost_rate - the signal engine has no knowledge of costs, only the execution
accounting does - so every stress scenario below executes the IDENTICAL
sequence of trades as a zero-cost run; only the price haircut applied to
each fill differs. This lets "gross return" be computed exactly once (0
commission, 0 slippage) and reused as the common baseline for every
scenario's cost breakdown, rather than approximated or estimated.

Commission and slippage are stress-tested SEPARATELY (not blended into one
"cost" dial): a fixed brokerage fee and a market-impact/price-movement cost
are economically different frictions, and testing them together would
obscure which one actually drives any survivability difference.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd

from app.backtesting.engine import run_backtest
from app.config import (
    COST_STRESS_COMMISSION_MULTIPLIERS,
    COST_STRESS_SLIPPAGE_LEVELS_BPS,
    MODEL_VERSION_CURRENT,
)
from app.services.exceptions import InsufficientHistoryError

COST_STRESS_METHODOLOGY = (
    "Every scenario re-runs the exact same backtest engine over the exact same period with the "
    "same signals - trade decisions never depend on transaction cost, so identical trades are "
    "executed in every scenario; only the price haircut applied to each fill changes. gross_return "
    "is the same backtest run with zero commission and zero slippage, computed once and reused as "
    "the baseline for every scenario's cost breakdown - never estimated or approximated. "
    "Commission and slippage are stress-tested independently (one held at its base value while the "
    "other varies) because they are economically different frictions. Surviving at higher cost "
    "multipliers is evidence the edge is not razor-thin relative to trading frictions - it is NOT "
    "by itself a claim of robustness across other dimensions (see Parameter Sensitivity)."
)


@dataclass
class CostStressScenario:
    label: str
    commission_bps: float
    slippage_bps: float
    net_return_percent: float | None
    total_cost_percent: float | None
    cagr_percent: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    max_drawdown_percent: float | None
    turnover_percent: float | None
    number_of_trades: int


@dataclass
class CostStressResult:
    ticker: str
    gross_return_percent: float | None
    commission_scenarios: list[CostStressScenario] = field(default_factory=list)
    slippage_scenarios: list[CostStressScenario] = field(default_factory=list)
    methodology: str = COST_STRESS_METHODOLOGY


def _run_scenario(
    label: str,
    ticker: str,
    full_price_df: pd.DataFrame,
    start_date: dt.date,
    end_date: dt.date,
    initial_capital: float,
    commission_bps: float,
    slippage_bps: float,
    model_version: str,
    gross_final_capital: float | None,
) -> CostStressScenario:
    try:
        result = run_backtest(
            ticker=ticker, full_price_df=full_price_df, start_date=start_date, end_date=end_date,
            initial_capital=initial_capital, transaction_cost_bps=commission_bps,
            slippage_bps=slippage_bps, model_version=model_version,
        )
    except InsufficientHistoryError:
        return CostStressScenario(
            label=label, commission_bps=commission_bps, slippage_bps=slippage_bps,
            net_return_percent=None, total_cost_percent=None, cagr_percent=None,
            sharpe_ratio=None, sortino_ratio=None, max_drawdown_percent=None,
            turnover_percent=None, number_of_trades=0,
        )

    total_cost_percent = None
    if gross_final_capital is not None and initial_capital > 0:
        total_cost_percent = round((gross_final_capital - result.final_capital) / initial_capital * 100.0, 2)

    return CostStressScenario(
        label=label,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        net_return_percent=result.total_return_percent,
        total_cost_percent=total_cost_percent,
        cagr_percent=result.advanced_metrics.get("cagr_percent"),
        sharpe_ratio=result.sharpe_ratio,
        sortino_ratio=result.advanced_metrics.get("sortino_ratio"),
        max_drawdown_percent=result.max_drawdown_percent,
        turnover_percent=result.advanced_metrics.get("turnover_percent"),
        number_of_trades=result.trade_stats.get("number_of_trades", 0),
    )


def run_cost_stress_test(
    ticker: str,
    full_price_df: pd.DataFrame,
    start_date: dt.date,
    end_date: dt.date,
    initial_capital: float,
    base_commission_bps: float,
    base_slippage_bps: float,
    model_version: str = MODEL_VERSION_CURRENT,
) -> CostStressResult:
    gross_final_capital = None
    gross_return_percent = None
    try:
        gross = run_backtest(
            ticker=ticker, full_price_df=full_price_df, start_date=start_date, end_date=end_date,
            initial_capital=initial_capital, transaction_cost_bps=0.0, slippage_bps=0.0,
            model_version=model_version,
        )
        gross_final_capital = gross.final_capital
        gross_return_percent = gross.total_return_percent
    except InsufficientHistoryError:
        pass

    commission_scenarios = [
        _run_scenario(
            label, ticker, full_price_df, start_date, end_date, initial_capital,
            commission_bps=base_commission_bps * multiplier, slippage_bps=base_slippage_bps,
            model_version=model_version, gross_final_capital=gross_final_capital,
        )
        for label, multiplier in COST_STRESS_COMMISSION_MULTIPLIERS.items()
    ]

    slippage_scenarios = [
        _run_scenario(
            f"{level:.2f}bps", ticker, full_price_df, start_date, end_date, initial_capital,
            commission_bps=base_commission_bps, slippage_bps=level,
            model_version=model_version, gross_final_capital=gross_final_capital,
        )
        for level in COST_STRESS_SLIPPAGE_LEVELS_BPS
    ]

    return CostStressResult(
        ticker=ticker,
        gross_return_percent=gross_return_percent,
        commission_scenarios=commission_scenarios,
        slippage_scenarios=slippage_scenarios,
    )
