"""Monte Carlo robustness / stress analysis over a backtest's own historical
returns. This is a bootstrap resampling stress test, not a forecast - it
answers "how sensitive was this result to the specific sequence of trades
that happened to occur?", not "what will happen next."

Unlike the deterministic signal engine, this module genuinely uses
randomness (that's the point of a Monte Carlo simulation) - callers that
need reproducible output (e.g. tests) should pass an explicit `seed`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.backtesting.metrics import Trade
from app.config import (
    MONTE_CARLO_METHODOLOGY,
    MONTE_CARLO_MIN_TRADES_FOR_TRADE_RESAMPLING,
)


@dataclass
class MonteCarloResult:
    simulations: int
    resampling_basis: str  # "trade_returns" | "daily_returns" | "unavailable"
    sample_size: int
    median_return_percent: float | None
    percentile_5_return_percent: float | None
    percentile_95_return_percent: float | None
    median_max_drawdown_percent: float | None
    worst_max_drawdown_percent: float | None
    methodology: str = MONTE_CARLO_METHODOLOGY


def run_monte_carlo(
    trades: list[Trade],
    daily_returns: pd.Series,
    initial_capital: float,
    num_simulations: int,
    seed: int | None = None,
) -> MonteCarloResult:
    trade_returns = [t.pnl_pct / 100.0 for t in trades if t.pnl_pct is not None]

    if len(trade_returns) >= MONTE_CARLO_MIN_TRADES_FOR_TRADE_RESAMPLING:
        sample = np.array(trade_returns)
        basis = "trade_returns"
    else:
        sample = daily_returns.dropna().to_numpy()
        basis = "daily_returns"

    if sample.size == 0:
        return MonteCarloResult(
            simulations=0,
            resampling_basis="unavailable",
            sample_size=0,
            median_return_percent=None,
            percentile_5_return_percent=None,
            percentile_95_return_percent=None,
            median_max_drawdown_percent=None,
            worst_max_drawdown_percent=None,
        )

    rng = np.random.default_rng(seed)
    n = sample.size

    final_returns = np.empty(num_simulations)
    max_drawdowns = np.empty(num_simulations)

    for i in range(num_simulations):
        draws = rng.choice(sample, size=n, replace=True)
        equity = initial_capital * np.cumprod(1.0 + draws)
        final_returns[i] = (equity[-1] / initial_capital - 1.0) * 100.0
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        max_drawdowns[i] = drawdown.min() * 100.0

    return MonteCarloResult(
        simulations=num_simulations,
        resampling_basis=basis,
        sample_size=n,
        median_return_percent=round(float(np.median(final_returns)), 2),
        percentile_5_return_percent=round(float(np.percentile(final_returns, 5)), 2),
        percentile_95_return_percent=round(float(np.percentile(final_returns, 95)), 2),
        median_max_drawdown_percent=round(float(np.median(max_drawdowns)), 2),
        worst_max_drawdown_percent=round(float(np.min(max_drawdowns)), 2),
    )
