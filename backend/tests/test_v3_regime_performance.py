"""Tests for regime-performance: grouping a backtest's own realized daily
returns and trades by which benchmark regime was active on each day.
"""
import pytest

from app.backtesting.engine import run_backtest
from app.market.regime_performance import compute_regime_performance


def test_regime_performance_handles_tz_aware_benchmark_index(ohlcv_long, ohlcv_uptrend):
    """Real yfinance data has a timezone-aware DatetimeIndex (e.g.
    America/New_York); the synthetic fixtures used elsewhere in this file
    are timezone-naive and would silently miss a naive-vs-aware comparison
    bug. This test localizes the benchmark fixture to reproduce that
    real-world shape and is a regression test for exactly that crash.
    """
    tz_aware_benchmark = ohlcv_uptrend.tz_localize("America/New_York")

    backtest_result = run_backtest(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    result = compute_regime_performance(
        ticker="TEST",
        benchmark="BENCH",
        backtest_result=backtest_result,
        benchmark_full_price_df=tz_aware_benchmark,
    )
    assert sum(b.trading_days for b in result.buckets) == len(backtest_result.strategy_curve)


def test_regime_performance_buckets_sum_to_total_days(ohlcv_long, ohlcv_uptrend):
    backtest_result = run_backtest(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    result = compute_regime_performance(
        ticker="TEST",
        benchmark="BENCH",
        backtest_result=backtest_result,
        benchmark_full_price_df=ohlcv_uptrend,
    )
    total_days_in_buckets = sum(b.trading_days for b in result.buckets)
    assert total_days_in_buckets == len(backtest_result.strategy_curve)


def test_regime_performance_frequency_percentages_sum_to_100(ohlcv_long, ohlcv_uptrend):
    backtest_result = run_backtest(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    result = compute_regime_performance(
        ticker="TEST", benchmark="BENCH", backtest_result=backtest_result, benchmark_full_price_df=ohlcv_uptrend,
    )
    total_pct = sum(b.frequency_percent for b in result.buckets)
    assert total_pct == pytest.approx(100.0, abs=1.0)


def test_regime_performance_trades_are_bucketed_by_entry_date(ohlcv_long, ohlcv_uptrend):
    backtest_result = run_backtest(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    result = compute_regime_performance(
        ticker="TEST", benchmark="BENCH", backtest_result=backtest_result, benchmark_full_price_df=ohlcv_uptrend,
    )
    total_bucketed_trades = sum(b.number_of_trades for b in result.buckets)
    assert total_bucketed_trades == len(backtest_result.trades)


def test_regime_performance_win_rate_bounded(ohlcv_long, ohlcv_uptrend):
    backtest_result = run_backtest(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    result = compute_regime_performance(
        ticker="TEST", benchmark="BENCH", backtest_result=backtest_result, benchmark_full_price_df=ohlcv_uptrend,
    )
    for b in result.buckets:
        if b.win_rate_percent is not None:
            assert 0.0 <= b.win_rate_percent <= 100.0
