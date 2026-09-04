"""Monte Carlo robustness / stress analysis over a backtest's own historical
returns. This is a bootstrap resampling stress test, not a forecast - it
answers "how sensitive was this result to the specific sequence of trades
that happened to occur?", not "what will happen next."

Unlike the deterministic signal engine, this module genuinely uses
randomness (that's the point of a Monte Carlo simulation) - callers that
need reproducible output (e.g. tests) should pass an explicit `seed`. The
same (sample, num_simulations, seed) always produces the same output -
`numpy.random.default_rng` is a deterministic PRNG given a fixed seed.

Resampling methodology (V5): trade-level returns are resampled as
independent draws (IID bootstrap) - each closed trade is a reasonably
distinct economic event, so treating them as exchangeable is a defensible
simplification. Daily returns, used only as a fallback when there are too
few discrete trades, are NOT resampled as independent draws: a long/flat
strategy's day-to-day returns are autocorrelated (a position persists
across many consecutive days), so an IID daily bootstrap would understate
real path risk by discarding that structure. The daily-returns fallback
therefore uses a BLOCK bootstrap - contiguous chunks of
`MONTE_CARLO_BLOCK_BOOTSTRAP_BLOCK_SIZE` consecutive days are resampled (with
replacement) and concatenated, preserving local autocorrelation within each
block while still bootstrapping the overall sequence.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.backtesting.metrics import Trade
from app.config import (
    HIST_VOL_ANNUALIZATION,
    MONTE_CARLO_BLOCK_BOOTSTRAP_BLOCK_SIZE,
    MONTE_CARLO_DEFAULT_DRAWDOWN_THRESHOLD_PERCENT,
    MONTE_CARLO_METHODOLOGY,
    MONTE_CARLO_MIN_TRADES_FOR_TRADE_RESAMPLING,
)


@dataclass
class MonteCarloResult:
    simulations: int
    resampling_basis: str  # "trade_returns" | "daily_returns" | "unavailable"
    resampling_method: str  # "iid_bootstrap" | "block_bootstrap" | "unavailable"
    sample_size: int
    seed: int | None
    median_return_percent: float | None
    percentile_5_return_percent: float | None
    percentile_95_return_percent: float | None
    median_max_drawdown_percent: float | None
    worst_max_drawdown_percent: float | None
    median_cagr_percent: float | None = None
    percentile_5_cagr_percent: float | None = None
    percentile_95_cagr_percent: float | None = None
    median_final_equity: float | None = None
    percentile_5_final_equity: float | None = None
    percentile_95_final_equity: float | None = None
    probability_of_loss_percent: float | None = None
    drawdown_threshold_percent: float = MONTE_CARLO_DEFAULT_DRAWDOWN_THRESHOLD_PERCENT
    probability_of_exceeding_drawdown_threshold_percent: float | None = None
    methodology: str = MONTE_CARLO_METHODOLOGY


def _block_bootstrap(rng: np.random.Generator, sample: np.ndarray, n: int, block_size: int) -> np.ndarray:
    if len(sample) <= block_size:
        return rng.choice(sample, size=n, replace=True)

    max_start = len(sample) - block_size
    pieces: list[np.ndarray] = []
    total = 0
    while total < n:
        start = int(rng.integers(0, max_start + 1))
        block = sample[start : start + block_size]
        pieces.append(block)
        total += block_size
    return np.concatenate(pieces)[:n]


def run_monte_carlo(
    trades: list[Trade],
    daily_returns: pd.Series,
    initial_capital: float,
    num_simulations: int,
    seed: int | None = None,
    drawdown_threshold_percent: float = MONTE_CARLO_DEFAULT_DRAWDOWN_THRESHOLD_PERCENT,
    trading_days_in_period: int | None = None,
) -> MonteCarloResult:
    trade_returns = [t.pnl_pct / 100.0 for t in trades if t.pnl_pct is not None]

    if len(trade_returns) >= MONTE_CARLO_MIN_TRADES_FOR_TRADE_RESAMPLING:
        sample = np.array(trade_returns)
        basis = "trade_returns"
        method = "iid_bootstrap"
    else:
        sample = daily_returns.dropna().to_numpy()
        basis = "daily_returns"
        method = "block_bootstrap"

    if sample.size == 0:
        return MonteCarloResult(
            simulations=0,
            resampling_basis="unavailable",
            resampling_method="unavailable",
            sample_size=0,
            seed=seed,
            median_return_percent=None,
            percentile_5_return_percent=None,
            percentile_95_return_percent=None,
            median_max_drawdown_percent=None,
            worst_max_drawdown_percent=None,
            drawdown_threshold_percent=drawdown_threshold_percent,
        )

    rng = np.random.default_rng(seed)
    n = sample.size
    years = (trading_days_in_period or n) / HIST_VOL_ANNUALIZATION

    final_returns = np.empty(num_simulations)
    final_equities = np.empty(num_simulations)
    max_drawdowns = np.empty(num_simulations)
    cagrs = np.full(num_simulations, np.nan)

    for i in range(num_simulations):
        draws = _block_bootstrap(rng, sample, n, MONTE_CARLO_BLOCK_BOOTSTRAP_BLOCK_SIZE) if method == "block_bootstrap" else rng.choice(sample, size=n, replace=True)
        equity = initial_capital * np.cumprod(1.0 + draws)
        final_equities[i] = equity[-1]
        final_returns[i] = (equity[-1] / initial_capital - 1.0) * 100.0
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        max_drawdowns[i] = drawdown.min() * 100.0
        growth = equity[-1] / initial_capital
        if growth > 0 and years > 0:
            cagrs[i] = (growth ** (1.0 / years) - 1.0) * 100.0

    valid_cagrs = cagrs[~np.isnan(cagrs)]

    return MonteCarloResult(
        simulations=num_simulations,
        resampling_basis=basis,
        resampling_method=method,
        sample_size=n,
        seed=seed,
        median_return_percent=round(float(np.median(final_returns)), 2),
        percentile_5_return_percent=round(float(np.percentile(final_returns, 5)), 2),
        percentile_95_return_percent=round(float(np.percentile(final_returns, 95)), 2),
        median_max_drawdown_percent=round(float(np.median(max_drawdowns)), 2),
        worst_max_drawdown_percent=round(float(np.min(max_drawdowns)), 2),
        median_cagr_percent=round(float(np.median(valid_cagrs)), 2) if valid_cagrs.size else None,
        percentile_5_cagr_percent=round(float(np.percentile(valid_cagrs, 5)), 2) if valid_cagrs.size else None,
        percentile_95_cagr_percent=round(float(np.percentile(valid_cagrs, 95)), 2) if valid_cagrs.size else None,
        median_final_equity=round(float(np.median(final_equities)), 2),
        percentile_5_final_equity=round(float(np.percentile(final_equities, 5)), 2),
        percentile_95_final_equity=round(float(np.percentile(final_equities, 95)), 2),
        probability_of_loss_percent=round(float(np.mean(final_returns < 0)) * 100.0, 2),
        drawdown_threshold_percent=drawdown_threshold_percent,
        probability_of_exceeding_drawdown_threshold_percent=round(
            float(np.mean(max_drawdowns <= drawdown_threshold_percent)) * 100.0, 2
        ),
    )
