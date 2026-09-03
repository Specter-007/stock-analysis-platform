"""Tests for the extended quant metrics suite (CAGR, Sortino, Calmar,
average drawdown, recovery time, expectancy, exposure, turnover, beta/alpha)
added for the Model Evaluation surfaces. Pure functions, synthetic fixtures.
"""
import numpy as np
import pandas as pd
import pytest

from app.backtesting import metrics as m
from app.backtesting.metrics import Trade


def test_cagr_matches_annualized_return():
    assert m.cagr(100, 200, 252) == pytest.approx(m.annualized_return(100, 200, 252))


def test_annualized_volatility_zero_for_constant_returns():
    returns = pd.Series([0.0] * 30)
    assert m.annualized_volatility_percent(returns) is None or m.annualized_volatility_percent(returns) == 0.0


def test_annualized_volatility_positive_for_varying_returns():
    rng = np.random.default_rng(1)
    returns = pd.Series(rng.normal(0, 0.01, 100))
    vol = m.annualized_volatility_percent(returns)
    assert vol is not None and vol > 0


def test_sortino_none_for_no_downside():
    returns = pd.Series([0.001] * 30)
    assert m.sortino_ratio(returns) is None


def test_sortino_positive_for_mostly_up_with_small_downside():
    returns = pd.Series([0.01, 0.01, 0.01, -0.001, 0.01, 0.01, -0.001, 0.01] * 5)
    result = m.sortino_ratio(returns)
    assert result is not None and result > 0


def test_calmar_ratio_basic():
    assert m.calmar_ratio(20.0, -10.0) == pytest.approx(2.0)


def test_calmar_ratio_none_when_no_drawdown():
    assert m.calmar_ratio(20.0, 0.0) is None
    assert m.calmar_ratio(None, -10.0) is None


def test_average_drawdown_percent_matches_manual_calc():
    equity = pd.Series([100.0, 90.0, 100.0, 80.0, 100.0])
    # drawdowns: -10% then -20%, average of the two = -15%
    result = m.average_drawdown_percent(equity)
    assert result == pytest.approx(-15.0, abs=0.5)


def test_average_drawdown_zero_when_always_at_peak():
    equity = pd.Series([100.0, 110.0, 120.0, 130.0])
    assert m.average_drawdown_percent(equity) == 0.0


def test_recovery_days_finds_correct_span():
    dates = pd.bdate_range("2024-01-01", periods=10)
    equity = pd.Series([100, 110, 90, 95, 105, 111, 112, 108, 109, 115], index=dates, dtype=float)
    # peak of 110 at index 1, trough 90 at index 2, recovers >=110 at index 5 (111)
    days = m.max_drawdown_recovery_days(equity)
    assert days == 3


def test_recovery_days_none_when_never_recovers():
    dates = pd.bdate_range("2024-01-01", periods=5)
    equity = pd.Series([100, 110, 90, 85, 80], index=dates, dtype=float)
    assert m.max_drawdown_recovery_days(equity) is None


def test_expectancy_matches_manual_average():
    trades = [
        Trade("2024-01-01", 100, "2024-01-02", 110, 10, pnl=100.0, pnl_pct=10.0),
        Trade("2024-01-03", 100, "2024-01-04", 90, 10, pnl=-100.0, pnl_pct=-10.0),
        Trade("2024-01-05", 100, "2024-01-06", 120, 10, pnl=200.0, pnl_pct=20.0),
    ]
    assert m.expectancy(trades) == pytest.approx((100 - 100 + 200) / 3, abs=0.01)


def test_expectancy_none_when_no_closed_trades():
    assert m.expectancy([]) is None


def test_average_win_loss_split_correctly():
    trades = [
        Trade("2024-01-01", 100, "2024-01-02", 110, 10, pnl=100.0, pnl_pct=10.0),
        Trade("2024-01-03", 100, "2024-01-04", 90, 10, pnl=-50.0, pnl_pct=-5.0),
        Trade("2024-01-05", 100, "2024-01-06", 120, 10, pnl=200.0, pnl_pct=20.0),
    ]
    result = m.average_win_loss(trades)
    assert result["average_win"] == pytest.approx(150.0)
    assert result["average_loss"] == pytest.approx(-50.0)
    assert result["average_win_percent"] == pytest.approx(15.0)
    assert result["average_loss_percent"] == pytest.approx(-5.0)


def test_exposure_percent_full_when_always_in_position():
    trades = [Trade("2024-01-01", 100, "2024-01-31", 110, 10, pnl=100.0, pnl_pct=10.0)]
    exposure = m.exposure_percent(trades, trading_days=22)
    assert exposure is not None and exposure > 0


def test_exposure_percent_zero_when_no_trades():
    assert m.exposure_percent([], trading_days=100) == 0.0


def test_turnover_percent_scales_with_trade_size():
    small = [Trade("2024-01-01", 100, "2024-01-02", 100, 1, pnl=0.0, pnl_pct=0.0)]
    large = [Trade("2024-01-01", 100, "2024-01-02", 100, 100, pnl=0.0, pnl_pct=0.0)]
    small_turnover = m.turnover_percent(small, initial_capital=10_000)
    large_turnover = m.turnover_percent(large, initial_capital=10_000)
    assert large_turnover > small_turnover


def test_beta_alpha_identical_series_gives_beta_one_alpha_zero():
    rng = np.random.default_rng(3)
    returns = pd.Series(rng.normal(0.0005, 0.01, 100))
    result = m.beta_alpha_tracking_error(returns, returns)
    assert result["beta"] == pytest.approx(1.0, abs=0.02)
    assert result["alpha_percent"] == pytest.approx(0.0, abs=0.5)
    assert result["tracking_error_percent"] == pytest.approx(0.0, abs=0.01)


def test_beta_alpha_none_with_insufficient_data():
    short = pd.Series([0.01, 0.02])
    result = m.beta_alpha_tracking_error(short, short)
    assert result["beta"] is None
    assert result["information_ratio"] is None


def test_beta_higher_for_more_volatile_strategy():
    rng = np.random.default_rng(4)
    benchmark = pd.Series(rng.normal(0.0003, 0.008, 200))
    amplified = benchmark * 2.0  # a 2x-levered clone should show beta ~2
    result = m.beta_alpha_tracking_error(amplified, benchmark)
    assert result["beta"] == pytest.approx(2.0, abs=0.1)
