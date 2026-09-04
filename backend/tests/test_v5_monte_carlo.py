"""V5: Monte Carlo extensions - CAGR/equity percentiles, loss probability,
drawdown-threshold probability, and block bootstrap for the daily-returns
fallback (documented as more appropriate than an IID daily bootstrap given
autocorrelation in a long/flat strategy's day-to-day returns).
"""
import numpy as np
import pandas as pd
import pytest

from app.backtesting.metrics import Trade
from app.backtesting.monte_carlo import run_monte_carlo


def _make_trades(n, win_rate=0.6, seed=1):
    rng = np.random.default_rng(seed)
    trades = []
    for i in range(n):
        won = rng.random() < win_rate
        pnl_pct = rng.uniform(2, 15) if won else -rng.uniform(2, 10)
        trades.append(Trade(
            entry_date=f"2023-01-{i+1:02d}", entry_price=100.0, exit_date=f"2023-02-{i+1:02d}",
            exit_price=100.0 * (1 + pnl_pct / 100), shares=10.0, pnl=pnl_pct, pnl_pct=pnl_pct,
        ))
    return trades


def _make_daily_returns(n=200, seed=2):
    rng = np.random.default_rng(seed)
    # Autocorrelated: today's return partly persists from yesterday's sign,
    # mimicking a long/flat strategy holding a position across many days.
    returns = np.zeros(n)
    returns[0] = rng.normal(0, 0.01)
    for i in range(1, n):
        returns[i] = 0.6 * returns[i - 1] + rng.normal(0, 0.008)
    return pd.Series(returns)


def test_trade_basis_uses_iid_bootstrap():
    trades = _make_trades(20)
    result = run_monte_carlo(trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=200, seed=1)
    assert result.resampling_basis == "trade_returns"
    assert result.resampling_method == "iid_bootstrap"


def test_daily_returns_basis_uses_block_bootstrap():
    result = run_monte_carlo([], _make_daily_returns(), initial_capital=10_000, num_simulations=200, seed=1)
    assert result.resampling_basis == "daily_returns"
    assert result.resampling_method == "block_bootstrap"


def test_cagr_percentiles_are_ordered_and_present():
    trades = _make_trades(20)
    result = run_monte_carlo(trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=500, seed=1)
    assert result.percentile_5_cagr_percent is not None
    assert result.median_cagr_percent is not None
    assert result.percentile_95_cagr_percent is not None
    assert result.percentile_5_cagr_percent <= result.median_cagr_percent <= result.percentile_95_cagr_percent


def test_final_equity_percentiles_are_ordered():
    trades = _make_trades(20)
    result = run_monte_carlo(trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=500, seed=1)
    assert result.percentile_5_final_equity <= result.median_final_equity <= result.percentile_95_final_equity


def test_probability_of_loss_between_zero_and_hundred():
    trades = _make_trades(20)
    result = run_monte_carlo(trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=500, seed=1)
    assert 0.0 <= result.probability_of_loss_percent <= 100.0


def test_all_losing_trades_gives_high_loss_probability():
    trades = _make_trades(20, win_rate=0.0)
    result = run_monte_carlo(trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=300, seed=1)
    assert result.probability_of_loss_percent > 90.0


def test_all_winning_trades_gives_zero_loss_probability():
    trades = _make_trades(20, win_rate=1.0)
    result = run_monte_carlo(trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=300, seed=1)
    assert result.probability_of_loss_percent == 0.0


def test_drawdown_threshold_probability_respects_custom_threshold():
    trades = _make_trades(20)
    result_tight = run_monte_carlo(
        trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=500, seed=1,
        drawdown_threshold_percent=-5.0,
    )
    result_loose = run_monte_carlo(
        trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=500, seed=1,
        drawdown_threshold_percent=-80.0,
    )
    # A shallower (less negative) threshold is easier to exceed than a much
    # deeper one, so its probability must be >= the deeper threshold's.
    assert result_tight.probability_of_exceeding_drawdown_threshold_percent >= result_loose.probability_of_exceeding_drawdown_threshold_percent


def test_seed_reproducibility_extends_to_new_fields():
    trades = _make_trades(20)
    r1 = run_monte_carlo(trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=300, seed=99)
    r2 = run_monte_carlo(trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=300, seed=99)
    assert r1.median_cagr_percent == r2.median_cagr_percent
    assert r1.probability_of_loss_percent == r2.probability_of_loss_percent
    assert r1.median_final_equity == r2.median_final_equity


def test_seed_and_methodology_reported_in_result():
    trades = _make_trades(20)
    result = run_monte_carlo(trades, pd.Series(dtype=float), initial_capital=10_000, num_simulations=100, seed=42)
    assert result.seed == 42


def test_block_bootstrap_preserves_more_variance_than_shuffling_would_erase():
    """Not a strict mathematical proof, but a sanity check that the block
    bootstrap actually produces a spread of outcomes (not a degenerate
    single-path result) when given autocorrelated daily returns.
    """
    daily = _make_daily_returns(n=250, seed=5)
    result = run_monte_carlo([], daily, initial_capital=10_000, num_simulations=300, seed=3)
    assert result.percentile_95_return_percent > result.percentile_5_return_percent


def test_unavailable_when_no_data_reports_new_fields_as_none():
    result = run_monte_carlo([], pd.Series(dtype=float), initial_capital=10_000, num_simulations=100)
    assert result.resampling_basis == "unavailable"
    assert result.resampling_method == "unavailable"
    assert result.median_cagr_percent is None
    assert result.probability_of_loss_percent is None
