"""Tests for parameter sensitivity analysis and in-sample/validation/
out-of-sample period splitting.
"""
import datetime as dt

import pytest

from app.backtesting.out_of_sample import run_out_of_sample_validation
from app.backtesting.sensitivity import run_sensitivity_analysis
from app.services.exceptions import InsufficientHistoryError


def test_sensitivity_buy_threshold_produces_one_point_per_value(ohlcv_long):
    result = run_sensitivity_analysis(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    buy_param = next(p for p in result.parameters if p.parameter == "buy_threshold")
    assert len(buy_param.points) == 5
    assert any(p.is_default for p in buy_param.points)


def test_sensitivity_reproducible_given_same_inputs(ohlcv_long):
    kwargs = dict(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    r1 = run_sensitivity_analysis(**kwargs)
    r2 = run_sensitivity_analysis(**kwargs)
    for p1, p2 in zip(r1.parameters, r2.parameters):
        assert [pt.total_return_percent for pt in p1.points] == [pt.total_return_percent for pt in p2.points]


def test_sensitivity_detects_inert_parameter(ohlcv_long):
    """The long/flat engine's entry/exit only checks whether the signal is
    BUY-class - the SELL/STRONG_SELL boundary (sell_threshold) therefore
    cannot change a single trade, at any tested value. This must be
    detected and labeled PARAMETER_INERT, never reported as 'robust'
    performance (which would misrepresent 'has no effect' as 'is stable').
    """
    result = run_sensitivity_analysis(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    sell_param = next(p for p in result.parameters if p.parameter == "sell_threshold")
    returns = [p.total_return_percent for p in sell_param.points if p.total_return_percent is not None]
    if len(set(returns)) == 1:
        assert sell_param.robustness == "PARAMETER_INERT"
        assert sell_param.note is not None


def test_sensitivity_flags_low_robustness_for_wildly_varying_returns(monkeypatch, ohlcv_long):
    """Force each backtest variant to return an alternating-sign result to
    prove LOW_ROBUSTNESS actually triggers, rather than only ever observing
    HIGHER_ROBUSTNESS/PARAMETER_INERT on real fixtures.
    """
    from app.backtesting import sensitivity as sens_module

    calls = {"n": 0}

    class FakeResult:
        def __init__(self, n):
            sign = 1 if n % 2 == 0 else -1
            self.total_return_percent = sign * 50.0
            self.advanced_metrics = {"cagr_percent": sign * 10.0}
            self.sharpe_ratio = sign * 0.5
            self.max_drawdown_percent = -20.0
            self.trade_stats = {"number_of_trades": 5}

    def fake_run_backtest(**kwargs):
        calls["n"] += 1
        return FakeResult(calls["n"])

    monkeypatch.setattr(sens_module, "run_backtest", fake_run_backtest)

    result = sens_module.run_sensitivity_analysis(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    buy_param = next(p for p in result.parameters if p.parameter == "buy_threshold")
    assert buy_param.robustness == "LOW_ROBUSTNESS"


def _split_dates(df):
    n = len(df)
    return {
        "in_sample_start": df.index[0].date(),
        "in_sample_end": df.index[n // 3].date(),
        "validation_start": df.index[n // 3 + 1].date(),
        "validation_end": df.index[2 * n // 3].date(),
        "out_of_sample_start": df.index[2 * n // 3 + 1].date(),
        "out_of_sample_end": df.index[-1].date(),
    }


def test_out_of_sample_produces_three_labeled_periods(ohlcv_long):
    dates = _split_dates(ohlcv_long)
    windows = [
        ("IN_SAMPLE", dates["in_sample_start"], dates["in_sample_end"]),
        ("VALIDATION", dates["validation_start"], dates["validation_end"]),
        ("OUT_OF_SAMPLE", dates["out_of_sample_start"], dates["out_of_sample_end"]),
    ]
    result = run_out_of_sample_validation(
        ticker="TEST", full_price_df=ohlcv_long, windows=windows,
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    labels = [p.label for p in result.periods]
    assert labels == ["IN_SAMPLE", "VALIDATION", "OUT_OF_SAMPLE"]


def test_out_of_sample_periods_are_chronological_and_non_overlapping(ohlcv_long):
    dates = _split_dates(ohlcv_long)
    windows = [
        ("IN_SAMPLE", dates["in_sample_start"], dates["in_sample_end"]),
        ("VALIDATION", dates["validation_start"], dates["validation_end"]),
        ("OUT_OF_SAMPLE", dates["out_of_sample_start"], dates["out_of_sample_end"]),
    ]
    result = run_out_of_sample_validation(
        ticker="TEST", full_price_df=ohlcv_long, windows=windows,
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    ends_and_starts = [(p.start_date, p.end_date) for p in result.periods]
    for (start, end) in ends_and_starts:
        assert dt.date.fromisoformat(start) < dt.date.fromisoformat(end)
    assert ends_and_starts[0][1] <= ends_and_starts[1][0]
    assert ends_and_starts[1][1] <= ends_and_starts[2][0]


def test_out_of_sample_uses_same_deterministic_engine_as_single_backtest(ohlcv_long):
    """An out-of-sample period's numbers must exactly match what a plain
    run_backtest() call over the identical date range would produce - this
    is not a separately-implemented strategy.
    """
    from app.backtesting.engine import run_backtest

    dates = _split_dates(ohlcv_long)
    windows = [("OUT_OF_SAMPLE", dates["out_of_sample_start"], dates["out_of_sample_end"])]

    oos_result = run_out_of_sample_validation(
        ticker="TEST", full_price_df=ohlcv_long, windows=windows,
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    direct_result = run_backtest(
        ticker="TEST", full_price_df=ohlcv_long,
        start_date=dates["out_of_sample_start"], end_date=dates["out_of_sample_end"],
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    assert oos_result.periods[0].total_return_percent == direct_result.total_return_percent
    assert oos_result.periods[0].sharpe_ratio == direct_result.sharpe_ratio


def test_out_of_sample_handles_insufficient_history_gracefully(ohlcv_long):
    windows = [("OUT_OF_SAMPLE", ohlcv_long.index[-5].date(), ohlcv_long.index[-1].date())]
    result = run_out_of_sample_validation(
        ticker="TEST", full_price_df=ohlcv_long, windows=windows,
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    assert result.periods[0].error is not None
    assert result.periods[0].total_return_percent is None
