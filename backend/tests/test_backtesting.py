import datetime as dt

import pandas as pd
import pytest

from app.backtesting import metrics as m
from app.backtesting.engine import run_backtest
from app.backtesting.metrics import Trade
from app.services.exceptions import InsufficientHistoryError


def _date_range(df: pd.DataFrame, skip_start: int = 210):
    """Pick a start/end date range with enough leading history for full
    indicator warmup (SMA 200 needs ~200 trading days)."""
    start = df.index[skip_start].date()
    end = df.index[-1].date()
    return start, end


def test_run_backtest_produces_bounded_equity_curve(ohlcv_long):
    start, end = _date_range(ohlcv_long)
    result = run_backtest(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=start,
        end_date=end,
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    assert result.initial_capital == 10_000.0
    assert result.final_capital > 0
    assert len(result.strategy_curve) == result.trading_days
    assert all(p.equity > 0 for p in result.strategy_curve)


def test_run_backtest_raises_on_too_short_range(ohlcv_long):
    start = ohlcv_long.index[-10].date()
    end = ohlcv_long.index[-1].date()
    with pytest.raises(InsufficientHistoryError):
        run_backtest(
            ticker="TEST",
            full_price_df=ohlcv_long,
            start_date=start,
            end_date=end,
            initial_capital=10_000.0,
            transaction_cost_bps=5,
            slippage_bps=5,
        )


def test_transaction_costs_reduce_returns_relative_to_zero_cost(ohlcv_uptrend):
    start, end = _date_range(ohlcv_uptrend)
    cheap = run_backtest(
        ticker="TEST", full_price_df=ohlcv_uptrend, start_date=start, end_date=end,
        initial_capital=10_000.0, transaction_cost_bps=0, slippage_bps=0,
    )
    expensive = run_backtest(
        ticker="TEST", full_price_df=ohlcv_uptrend, start_date=start, end_date=end,
        initial_capital=10_000.0, transaction_cost_bps=100, slippage_bps=100,
    )
    if cheap.trade_stats["number_of_trades"] > 0:
        assert expensive.final_capital <= cheap.final_capital


def test_slippage_reduces_final_capital_when_trades_occur(ohlcv_high_volatility):
    start, end = _date_range(ohlcv_high_volatility)
    no_slip = run_backtest(
        ticker="TEST", full_price_df=ohlcv_high_volatility, start_date=start, end_date=end,
        initial_capital=10_000.0, transaction_cost_bps=0, slippage_bps=0,
    )
    with_slip = run_backtest(
        ticker="TEST", full_price_df=ohlcv_high_volatility, start_date=start, end_date=end,
        initial_capital=10_000.0, transaction_cost_bps=0, slippage_bps=200,
    )
    if no_slip.trade_stats["number_of_trades"] > 0:
        assert with_slip.final_capital <= no_slip.final_capital


def test_no_look_ahead_prefix_invariance(ohlcv_long):
    """The strategy's behavior through day K must be identical whether the
    backtester is given data up through day K, or data extending further
    into the future. This directly tests the no-look-ahead-bias contract.
    """
    start, _ = _date_range(ohlcv_long)
    full_end = ohlcv_long.index[-1].date()
    shorter_end = ohlcv_long.index[-50].date()

    full_result = run_backtest(
        ticker="TEST", full_price_df=ohlcv_long, start_date=start, end_date=full_end,
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    truncated_result = run_backtest(
        ticker="TEST", full_price_df=ohlcv_long, start_date=start, end_date=shorter_end,
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )

    overlap_days = len(truncated_result.strategy_curve)
    full_prefix = full_result.strategy_curve[:overlap_days]
    truncated_curve = truncated_result.strategy_curve

    for a, b in zip(full_prefix, truncated_curve):
        assert a.date == b.date
        assert a.equity == pytest.approx(b.equity), (
            f"Equity on {a.date} differs depending on future data "
            f"({a.equity} vs {b.equity}) - this indicates look-ahead bias."
        )


def test_execution_happens_next_bar_not_same_bar(ohlcv_uptrend):
    """A trade's entry_price should equal (approximately) the OPEN of the day
    AFTER the signal's date, never the close of the signal's own day.
    """
    start, end = _date_range(ohlcv_uptrend)
    result = run_backtest(
        ticker="TEST", full_price_df=ohlcv_uptrend, start_date=start, end_date=end,
        initial_capital=10_000.0, transaction_cost_bps=0, slippage_bps=0,
    )
    for trade in result.trades:
        entry_date = pd.Timestamp(trade.entry_date)
        assert entry_date in ohlcv_uptrend.index
        actual_open = float(ohlcv_uptrend.loc[entry_date, "Open"])
        assert trade.entry_price == pytest.approx(actual_open, rel=1e-6)


def test_drawdown_metric_matches_manual_calculation():
    equity = pd.Series([100.0, 110.0, 90.0, 95.0, 120.0, 60.0])
    dd = m.max_drawdown_percent(equity)
    # Worst drop: 120 -> 60 = -50%
    assert dd == pytest.approx(-50.0)


def test_sharpe_ratio_none_for_constant_returns():
    returns = pd.Series([0.0] * 30)
    assert m.sharpe_ratio(returns) is None


def test_sharpe_ratio_positive_for_consistently_positive_returns():
    returns = pd.Series([0.001, 0.0015, 0.0008, 0.002, 0.0012] * 10)
    result = m.sharpe_ratio(returns)
    assert result is not None
    assert result > 0


def test_trade_stats_win_rate_and_profit_factor():
    trades = [
        Trade("2024-01-01", 100, "2024-01-05", 110, 10, pnl=100, pnl_pct=10.0),
        Trade("2024-02-01", 100, "2024-02-05", 90, 10, pnl=-100, pnl_pct=-10.0),
        Trade("2024-03-01", 100, "2024-03-05", 120, 10, pnl=200, pnl_pct=20.0),
    ]
    stats = m.trade_stats(trades)
    assert stats["number_of_trades"] == 3
    assert stats["winning_trades"] == 2
    assert stats["losing_trades"] == 1
    assert stats["win_rate_percent"] == pytest.approx(66.67, rel=1e-2)
    assert stats["profit_factor"] == pytest.approx(300 / 100)


def test_trade_stats_empty_when_no_closed_trades():
    stats = m.trade_stats([])
    assert stats["number_of_trades"] == 0
    assert stats["win_rate_percent"] is None
    assert stats["profit_factor"] is None


def test_total_return_and_annualized_return():
    assert m.total_return(100, 150) == pytest.approx(50.0)
    assert m.total_return(0, 150) is None
    ann = m.annualized_return(100, 200, 252)
    assert ann == pytest.approx(100.0, rel=1e-2)


def test_beta_alpha_present_with_tz_aware_equity_index(ohlcv_long, ohlcv_uptrend):
    """Regression test: real yfinance data has a timezone-AWARE index, while
    the benchmark equity curve's date strings are naive "YYYY-MM-DD". A
    previous version reindexed one against the other directly, which
    silently matched nothing and left beta/alpha/tracking-error/information-
    ratio None even with a perfectly valid benchmark supplied.
    """
    tz_aware_ticker = ohlcv_long.tz_localize("America/New_York")
    tz_aware_benchmark = ohlcv_uptrend.tz_localize("America/New_York")

    start, end = _date_range(tz_aware_ticker)
    result = run_backtest(
        ticker="TEST",
        full_price_df=tz_aware_ticker,
        start_date=start,
        end_date=end,
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
        benchmark_ticker="BENCH",
        benchmark_full_price_df=tz_aware_benchmark,
    )
    assert result.advanced_metrics["beta"] is not None
    assert result.advanced_metrics["tracking_error_percent"] is not None
