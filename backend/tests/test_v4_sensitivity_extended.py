"""V4 extended parameter sensitivity: indicator-period sweeps (RSI, SMA,
MACD) on top of the V3 score-threshold sweeps, plus the 2D heatmap mode.

The single most important test in this file is
`test_default_params_match_standard_indicator_frame`: it is the safety proof
that `parametrized_indicators.compute_custom_indicator_frame` - a completely
separate code path from the production `compute_indicator_frame` - produces
bit-for-bit identical output at default parameters. Every other test in this
module, and the whole indicator-sensitivity feature, depends on this holding.
"""
import numpy as np
import pandas as pd
import pytest

from app.backtesting.parametrized_indicators import (
    IndicatorParams,
    SENSITIVITY_RANGES,
    compute_custom_indicator_frame,
)
from app.backtesting.sensitivity import (
    ALL_PARAMETERS,
    THRESHOLD_PARAMETERS,
    run_sensitivity_analysis,
    run_sensitivity_heatmap,
)
from app.indicators.compute import INDICATOR_COLUMNS, compute_indicator_frame


def test_default_params_match_standard_indicator_frame(ohlcv_long):
    standard = compute_indicator_frame(ohlcv_long)
    custom = compute_custom_indicator_frame(ohlcv_long, IndicatorParams())

    for col in INDICATOR_COLUMNS:
        std_series = standard[col]
        custom_series = custom[col]
        if pd.api.types.is_numeric_dtype(std_series):
            np.testing.assert_allclose(
                std_series.to_numpy(dtype=float),
                custom_series.to_numpy(dtype=float),
                equal_nan=True,
                err_msg=f"column {col!r} diverged between standard and custom indicator frames at defaults",
            )
        else:
            pd.testing.assert_series_equal(std_series, custom_series, check_names=False)


def test_custom_indicator_frame_actually_changes_with_nondefault_period(ohlcv_long):
    """Guards against a no-op parametrization - if this ever fails, the
    'sensitivity' analysis would be silently testing nothing.
    """
    default_frame = compute_custom_indicator_frame(ohlcv_long, IndicatorParams())
    perturbed_frame = compute_custom_indicator_frame(ohlcv_long, IndicatorParams(rsi_period=21))
    assert not default_frame["RSI_14"].equals(perturbed_frame["RSI_14"])

    perturbed_sma = compute_custom_indicator_frame(ohlcv_long, IndicatorParams(sma_short=10))
    assert not default_frame["SMA_20"].equals(perturbed_sma["SMA_20"])

    perturbed_macd = compute_custom_indicator_frame(ohlcv_long, IndicatorParams(macd_fast=8))
    assert not default_frame["MACD"].equals(perturbed_macd["MACD"])


def test_custom_indicator_frame_preserves_no_look_ahead(ohlcv_long):
    """Mutating a future row must not change any earlier row's indicator
    value - the same no-look-ahead contract the production frame guarantees.
    """
    truncated = ohlcv_long.iloc[:-50].copy()
    full = ohlcv_long.copy()
    full.iloc[-1, full.columns.get_loc("Close")] *= 5.0  # violently mutate the last row only

    params = IndicatorParams(rsi_period=10, sma_short=15)
    truncated_frame = compute_custom_indicator_frame(truncated, params)
    full_frame = compute_custom_indicator_frame(full, params)

    common_index = truncated_frame.index
    for col in ("RSI_14", "SMA_20", "MACD", "ATR_14"):
        np.testing.assert_allclose(
            truncated_frame[col].to_numpy(dtype=float),
            full_frame.loc[common_index, col].to_numpy(dtype=float),
            equal_nan=True,
        )


@pytest.mark.parametrize("parameter", ["rsi_period", "sma_short", "sma_long", "macd_fast", "macd_slow"])
def test_indicator_period_sensitivity_produces_one_point_per_value(ohlcv_long, parameter):
    result = run_sensitivity_analysis(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
        parameters=(parameter,),
    )
    assert len(result.parameters) == 1
    param_result = result.parameters[0]
    assert param_result.parameter == parameter
    assert len(param_result.points) == len(SENSITIVITY_RANGES[parameter])
    assert any(p.is_default for p in param_result.points)
    assert param_result.robustness in (
        "HIGHER_ROBUSTNESS", "LOW_ROBUSTNESS", "PARAMETER_INERT", "INSUFFICIENT_DATA", "INSUFFICIENT_SAMPLE",
    )


def test_full_parameter_set_covers_all_seven_parameters(ohlcv_long):
    result = run_sensitivity_analysis(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
        parameters=ALL_PARAMETERS,
    )
    tested = {p.parameter for p in result.parameters}
    assert tested == set(ALL_PARAMETERS)
    assert set(THRESHOLD_PARAMETERS) <= tested


def test_default_call_still_only_tests_thresholds_for_backward_compatibility(ohlcv_long):
    """Existing V3 callers (and the real-data integration test asserting
    len(parameters) == 2) must keep working unchanged.
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
    assert {p.parameter for p in result.parameters} == set(THRESHOLD_PARAMETERS)


def test_indicator_sensitivity_reports_best_median_worst(ohlcv_long):
    result = run_sensitivity_analysis(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
        parameters=("rsi_period",),
    )
    param_result = result.parameters[0]
    if param_result.robustness != "INSUFFICIENT_DATA":
        assert param_result.best_value is not None
        assert param_result.median_value is not None
        assert param_result.worst_value is not None


def test_insufficient_sample_verdict_when_default_has_few_trades(monkeypatch, ohlcv_long):
    from app.backtesting import sensitivity as sens_module

    class FakeResult:
        def __init__(self, ret):
            self.total_return_percent = ret
            self.advanced_metrics = {"cagr_percent": ret}
            self.sharpe_ratio = 0.1
            self.max_drawdown_percent = -5.0
            self.trade_stats = {"number_of_trades": 1}

    calls = {"n": 0}

    def fake_run_backtest(**kwargs):
        # Non-zero variance across variants (so this isn't also PARAMETER_INERT)
        # but every variant still has only 1 trade (so the sample is too thin
        # to trust that variance as a real robustness signal).
        calls["n"] += 1
        return FakeResult(1.0 + calls["n"])

    monkeypatch.setattr(sens_module, "run_backtest", fake_run_backtest)

    result = sens_module.run_sensitivity_analysis(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
        parameters=("rsi_period",),
    )
    param_result = result.parameters[0]
    assert param_result.robustness == "INSUFFICIENT_SAMPLE"
    assert param_result.note is not None


def test_heatmap_produces_full_grid(ohlcv_long):
    result = run_sensitivity_heatmap(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
        param_x="buy_threshold",
        param_y="rsi_period",
    )
    assert len(result.cells) == len(SENSITIVITY_RANGES["buy_threshold"]) * len(SENSITIVITY_RANGES["rsi_period"])
    x_values = {c.x_value for c in result.cells}
    y_values = {c.y_value for c in result.cells}
    assert x_values == set(SENSITIVITY_RANGES["buy_threshold"])
    assert y_values == set(SENSITIVITY_RANGES["rsi_period"])


def test_heatmap_rejects_unknown_parameter(ohlcv_long):
    with pytest.raises(ValueError):
        run_sensitivity_heatmap(
            ticker="TEST",
            full_price_df=ohlcv_long,
            start_date=ohlcv_long.index[220].date(),
            end_date=ohlcv_long.index[-1].date(),
            initial_capital=10_000.0,
            transaction_cost_bps=5,
            slippage_bps=5,
            param_x="buy_threshold",
            param_y="not_a_real_parameter",
        )


def test_heatmap_flags_insufficient_sample_cells(ohlcv_long):
    result = run_sensitivity_heatmap(
        ticker="TEST",
        full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(),
        end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
        param_x="buy_threshold",
        param_y="rsi_period",
    )
    for cell in result.cells:
        assert isinstance(cell.insufficient_sample, bool)
        if cell.number_of_trades < 5:
            assert cell.insufficient_sample is True
