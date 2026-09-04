"""V5: transaction-cost and slippage stress testing."""
import pytest

from app.backtesting.cost_stress import run_cost_stress_test
from app.config import COST_STRESS_COMMISSION_MULTIPLIERS, COST_STRESS_SLIPPAGE_LEVELS_BPS


def _date_range(df, start_offset=220):
    return df.index[start_offset].date(), df.index[-1].date()


def test_commission_scenarios_cover_all_multipliers(ohlcv_long):
    start, end = _date_range(ohlcv_long)
    result = run_cost_stress_test(
        ticker="TEST", full_price_df=ohlcv_long, start_date=start, end_date=end,
        initial_capital=10_000.0, base_commission_bps=5.0, base_slippage_bps=5.0,
    )
    assert len(result.commission_scenarios) == len(COST_STRESS_COMMISSION_MULTIPLIERS)
    labels = {s.label for s in result.commission_scenarios}
    assert labels == set(COST_STRESS_COMMISSION_MULTIPLIERS.keys())


def test_slippage_scenarios_cover_all_levels(ohlcv_long):
    start, end = _date_range(ohlcv_long)
    result = run_cost_stress_test(
        ticker="TEST", full_price_df=ohlcv_long, start_date=start, end_date=end,
        initial_capital=10_000.0, base_commission_bps=5.0, base_slippage_bps=5.0,
    )
    assert len(result.slippage_scenarios) == len(COST_STRESS_SLIPPAGE_LEVELS_BPS)


def test_higher_commission_multiplier_never_produces_higher_net_return_than_lower(ohlcv_long):
    """Trades are identical across scenarios (costs don't affect the signal
    engine's decisions) - so strictly higher friction can only ever reduce
    (or leave unchanged, if there are zero trades) net return, never raise it.
    """
    start, end = _date_range(ohlcv_long)
    result = run_cost_stress_test(
        ticker="TEST", full_price_df=ohlcv_long, start_date=start, end_date=end,
        initial_capital=10_000.0, base_commission_bps=5.0, base_slippage_bps=5.0,
    )
    by_label = {s.label: s for s in result.commission_scenarios}
    ordered = [by_label[l] for l in ("BASE", "MODERATE", "HIGH", "EXTREME")]
    returns = [s.net_return_percent for s in ordered]
    for a, b in zip(returns, returns[1:]):
        assert b <= a + 1e-9


def test_all_scenarios_execute_the_same_number_of_trades(ohlcv_long):
    start, end = _date_range(ohlcv_long)
    result = run_cost_stress_test(
        ticker="TEST", full_price_df=ohlcv_long, start_date=start, end_date=end,
        initial_capital=10_000.0, base_commission_bps=5.0, base_slippage_bps=5.0,
    )
    trade_counts = {s.number_of_trades for s in result.commission_scenarios}
    assert len(trade_counts) == 1  # identical trade decisions regardless of cost


def test_total_cost_percent_increases_with_commission_multiplier(ohlcv_long):
    start, end = _date_range(ohlcv_long)
    result = run_cost_stress_test(
        ticker="TEST", full_price_df=ohlcv_long, start_date=start, end_date=end,
        initial_capital=10_000.0, base_commission_bps=5.0, base_slippage_bps=5.0,
    )
    by_label = {s.label: s for s in result.commission_scenarios}
    if by_label["BASE"].number_of_trades > 0:
        assert by_label["EXTREME"].total_cost_percent >= by_label["BASE"].total_cost_percent


def test_zero_slippage_scenario_present(ohlcv_long):
    start, end = _date_range(ohlcv_long)
    result = run_cost_stress_test(
        ticker="TEST", full_price_df=ohlcv_long, start_date=start, end_date=end,
        initial_capital=10_000.0, base_commission_bps=5.0, base_slippage_bps=5.0,
    )
    zero = next(s for s in result.slippage_scenarios if s.slippage_bps == 0.0)
    assert zero.commission_bps == 5.0  # commission held at base, only slippage varies


def test_gross_return_matches_zero_cost_backtest(ohlcv_long):
    from app.backtesting.engine import run_backtest

    start, end = _date_range(ohlcv_long)
    direct_gross = run_backtest(
        ticker="TEST", full_price_df=ohlcv_long, start_date=start, end_date=end,
        initial_capital=10_000.0, transaction_cost_bps=0.0, slippage_bps=0.0,
    )
    result = run_cost_stress_test(
        ticker="TEST", full_price_df=ohlcv_long, start_date=start, end_date=end,
        initial_capital=10_000.0, base_commission_bps=5.0, base_slippage_bps=5.0,
    )
    assert result.gross_return_percent == direct_gross.total_return_percent


def test_insufficient_history_does_not_crash(ohlcv_long):
    result = run_cost_stress_test(
        ticker="TEST", full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[-5].date(), end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0, base_commission_bps=5.0, base_slippage_bps=5.0,
    )
    assert result.gross_return_percent is None
    assert all(s.net_return_percent is None for s in result.commission_scenarios)
