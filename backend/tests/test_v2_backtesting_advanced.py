"""Tests for walk-forward analysis and Monte Carlo robustness simulation."""
import pandas as pd
import pytest

from app.backtesting.metrics import Trade
from app.backtesting.monte_carlo import run_monte_carlo
from app.backtesting.walk_forward import run_walk_forward


def test_walk_forward_produces_non_overlapping_recent_folds(ohlcv_long):
    result = run_walk_forward(
        ticker="TEST",
        full_price_df=ohlcv_long,
        train_years=0.5,
        test_years=0.25,
        max_folds=3,
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    assert len(result.folds) <= 3
    # Folds must be in chronological order and each test window starts
    # exactly where the previous one ended (or later).
    for a, b in zip(result.folds, result.folds[1:]):
        assert a.test_end <= b.test_start


def test_walk_forward_prefers_most_recent_folds_for_long_history():
    """For a long-listed ticker, requesting fewer folds than are possible
    must return the MOST RECENT ones, not the oldest - see the bug this
    guards against in walk_forward.py's docstring.
    """
    n = 3000
    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    import numpy as np

    rng = np.random.default_rng(5)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    df = pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1_000_000.0},
        index=index,
    )

    result = run_walk_forward(
        ticker="TEST", full_price_df=df, train_years=2, test_years=1, max_folds=2,
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    assert len(result.folds) == 2
    last_fold_test_end = pd.Timestamp(result.folds[-1].test_end)
    data_end = df.index[-1]
    # The most recent fold's test window must end close to the data's end,
    # not decades earlier.
    assert (data_end - last_fold_test_end).days < 400


def test_walk_forward_empty_for_empty_dataframe():
    result = run_walk_forward(
        ticker="TEST", full_price_df=pd.DataFrame(), train_years=1, test_years=1, max_folds=3,
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    assert result.folds == []
    assert result.average_test_return_percent is None


def test_monte_carlo_uses_trade_resampling_when_enough_trades():
    trades = [Trade(f"2024-01-{i:02d}", 100, f"2024-01-{i+1:02d}", 105, 10, pnl=50, pnl_pct=5.0) for i in range(1, 15)]
    daily_returns = pd.Series([0.001] * 30)
    result = run_monte_carlo(trades, daily_returns, initial_capital=10_000, num_simulations=200, seed=1)
    assert result.resampling_basis == "trade_returns"
    assert result.sample_size == 14
    assert result.simulations == 200


def test_monte_carlo_falls_back_to_daily_returns_when_too_few_trades():
    trades = [Trade("2024-01-01", 100, "2024-01-02", 105, 10, pnl=50, pnl_pct=5.0)]
    daily_returns = pd.Series([0.001, -0.002, 0.003, 0.0, 0.001] * 10)
    result = run_monte_carlo(trades, daily_returns, initial_capital=10_000, num_simulations=200, seed=1)
    assert result.resampling_basis == "daily_returns"


def test_monte_carlo_unavailable_when_no_data_at_all():
    result = run_monte_carlo([], pd.Series(dtype=float), initial_capital=10_000, num_simulations=100)
    assert result.resampling_basis == "unavailable"
    assert result.median_return_percent is None


def test_monte_carlo_reproducible_with_same_seed():
    trades = [Trade(f"2024-01-{i:02d}", 100, f"2024-01-{i+1:02d}", 105, 10, pnl=(-1) ** i * 20, pnl_pct=(-1) ** i * 2.0) for i in range(1, 20)]
    daily_returns = pd.Series([0.001] * 30)
    r1 = run_monte_carlo(trades, daily_returns, initial_capital=10_000, num_simulations=500, seed=42)
    r2 = run_monte_carlo(trades, daily_returns, initial_capital=10_000, num_simulations=500, seed=42)
    assert r1.median_return_percent == r2.median_return_percent
    assert r1.worst_max_drawdown_percent == r2.worst_max_drawdown_percent


def test_monte_carlo_percentiles_are_ordered():
    trades = [Trade(f"2024-01-{i:02d}", 100, f"2024-01-{i+1:02d}", 105, 10, pnl=(-1) ** i * 30, pnl_pct=(-1) ** i * 3.0) for i in range(1, 20)]
    daily_returns = pd.Series([0.001] * 30)
    result = run_monte_carlo(trades, daily_returns, initial_capital=10_000, num_simulations=500, seed=7)
    assert result.percentile_5_return_percent <= result.median_return_percent <= result.percentile_95_return_percent
