"""Parameter sensitivity analysis - the primary tool for detecting overfitting.

Perturbs one parameter at a time (or two, for a heatmap) around its default
value and re-runs the SAME backtest engine for each variant. The question
this answers is never "what is the best value?" - it is "does performance
hold up in the neighborhood of the chosen value, or does it collapse a few
points away in either direction?" A model whose backtest only looks good at
one exact parameter value is a strong overfitting warning sign.

V4 extends the V3 threshold-only version to include indicator periods
(RSI, short/long SMA, MACD fast/slow) via `parametrized_indicators.py`'s
isolated computation path - Quant v1.0/v1.1's own indicator computation
(`app.indicators.compute.compute_indicator_frame`) is never touched by this
module.
"""
from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass, field

import pandas as pd

from app.backtesting.engine import run_backtest
from app.backtesting.parametrized_indicators import (
    PARAMETER_LABELS,
    SENSITIVITY_RANGES,
    IndicatorParams,
    compute_custom_indicator_frame,
)
from app.config import MODEL_VERSION_CURRENT, SCORE_BUY, SCORE_SELL_LOW
from app.services.exceptions import InsufficientHistoryError
from app.signals.engine import ScoreThresholds

DEFAULT_VALUES = {
    "buy_threshold": SCORE_BUY,
    "sell_threshold": SCORE_SELL_LOW,
    "rsi_period": IndicatorParams().rsi_period,
    "sma_short": IndicatorParams().sma_short,
    "sma_long": IndicatorParams().sma_long,
    "macd_fast": IndicatorParams().macd_fast,
    "macd_slow": IndicatorParams().macd_slow,
}

THRESHOLD_PARAMETERS = ("buy_threshold", "sell_threshold")
ALL_PARAMETERS = tuple(SENSITIVITY_RANGES.keys())

MIN_TRADES_FOR_ROBUSTNESS_VERDICT = 5

ROBUSTNESS_METHODOLOGY = (
    "For each parameter, the coefficient of variation (std / |mean|) of total return across all "
    "tested values is computed. CV < 0.5 is labeled HIGHER_ROBUSTNESS (performance is reasonably "
    "stable across the neighborhood); CV >= 0.5 is labeled LOW_ROBUSTNESS. If every tested value "
    "produced an identical result, the parameter is labeled PARAMETER_INERT (it cannot affect this "
    "engine's trading decisions at all - reporting that as 'robust' would misrepresent 'no effect' "
    "as 'stable performance'). If the DEFAULT configuration produced fewer than 5 trades, the "
    "verdict is INSUFFICIENT_SAMPLE instead - a robustness classification from a handful of trades "
    "is not statistically meaningful. This is a documented heuristic, not a significance test."
)


@dataclass
class SensitivityPoint:
    parameter: str
    value: float
    is_default: bool
    total_return_percent: float | None
    cagr_percent: float | None
    sharpe_ratio: float | None
    max_drawdown_percent: float | None
    number_of_trades: int


@dataclass
class ParameterSensitivity:
    parameter: str
    label: str
    default_value: float
    points: list[SensitivityPoint] = field(default_factory=list)
    # HIGHER_ROBUSTNESS | LOW_ROBUSTNESS | INSUFFICIENT_DATA | PARAMETER_INERT | INSUFFICIENT_SAMPLE
    robustness: str = "INSUFFICIENT_DATA"
    robust_region_min: float | None = None
    robust_region_max: float | None = None
    best_value: float | None = None
    median_value: float | None = None
    worst_value: float | None = None
    note: str | None = None


@dataclass
class SensitivityResult:
    ticker: str
    model_version: str
    parameters: list[ParameterSensitivity] = field(default_factory=list)
    methodology: str = ROBUSTNESS_METHODOLOGY


def _run_variant(
    ticker: str,
    full_price_df: pd.DataFrame,
    start_date: dt.date,
    end_date: dt.date,
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
    model_version: str,
    parameter: str,
    value: float,
    is_default: bool,
    thresholds: ScoreThresholds,
    indicator_params: IndicatorParams,
) -> SensitivityPoint:
    try:
        precomputed = None
        if parameter not in THRESHOLD_PARAMETERS:
            precomputed = compute_custom_indicator_frame(full_price_df, indicator_params)

        result = run_backtest(
            ticker=ticker,
            full_price_df=full_price_df,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps,
            model_version=model_version,
            thresholds=thresholds,
            precomputed_indicator_df=precomputed,
        )
        return SensitivityPoint(
            parameter=parameter,
            value=value,
            is_default=is_default,
            total_return_percent=result.total_return_percent,
            cagr_percent=result.advanced_metrics.get("cagr_percent"),
            sharpe_ratio=result.sharpe_ratio,
            max_drawdown_percent=result.max_drawdown_percent,
            number_of_trades=result.trade_stats.get("number_of_trades", 0),
        )
    except InsufficientHistoryError:
        return SensitivityPoint(
            parameter=parameter, value=value, is_default=is_default,
            total_return_percent=None, cagr_percent=None, sharpe_ratio=None,
            max_drawdown_percent=None, number_of_trades=0,
        )


def _thresholds_for(parameter: str, value: float) -> ScoreThresholds:
    if parameter == "buy_threshold":
        return ScoreThresholds(buy=value)
    if parameter == "sell_threshold":
        return ScoreThresholds(sell_low=value)
    return ScoreThresholds()


def _indicator_params_for(parameter: str, value: float) -> IndicatorParams:
    overrides = {}
    if parameter in ("rsi_period", "sma_short", "sma_long", "macd_fast", "macd_slow"):
        overrides[parameter] = int(value)
    return IndicatorParams(**overrides)


def _summarize(points: list[SensitivityPoint], default_value: float) -> ParameterSensitivity:
    parameter = points[0].parameter
    valid = [p for p in points if p.total_return_percent is not None]
    default_point = next((p for p in points if p.is_default), None)

    result = ParameterSensitivity(
        parameter=parameter,
        label=PARAMETER_LABELS.get(parameter, parameter),
        default_value=default_value,
        points=points,
    )

    if len(valid) < 3:
        result.robustness = "INSUFFICIENT_DATA"
        return result

    if default_point and default_point.number_of_trades < MIN_TRADES_FOR_ROBUSTNESS_VERDICT:
        result.robustness = "INSUFFICIENT_SAMPLE"
        result.note = (
            f"The default configuration produced only {default_point.number_of_trades} trade(s) "
            f"over this period - too few for a meaningful robustness verdict."
        )

    returns = [p.total_return_percent for p in valid]
    ordered_by_return = sorted(valid, key=lambda p: p.total_return_percent)
    result.worst_value = ordered_by_return[0].value
    result.best_value = ordered_by_return[-1].value
    result.median_value = ordered_by_return[len(ordered_by_return) // 2].value

    mean_r = statistics.mean(returns)
    std_r = statistics.pstdev(returns)

    if std_r == 0:
        result.robustness = "PARAMETER_INERT"
        result.robust_region_min = min(p.value for p in valid)
        result.robust_region_max = max(p.value for p in valid)
        result.note = (
            "Every tested value produced an identical backtest result. This parameter does not "
            "affect the long/flat engine's entry/exit decision, so its 'robustness' here reflects "
            "having no effect, not stable performance."
        )
        return result

    if result.robustness != "INSUFFICIENT_SAMPLE":
        cv = (std_r / abs(mean_r)) if mean_r != 0 else float("inf")
        result.robustness = "HIGHER_ROBUSTNESS" if cv < 0.5 else "LOW_ROBUSTNESS"

    default_sign = 1 if (default_point and (default_point.total_return_percent or 0) >= 0) else -1
    ordered_by_value = sorted(valid, key=lambda p: p.value)
    default_idx = next((i for i, p in enumerate(ordered_by_value) if p.is_default), None)

    region_values: list[float] = []
    if default_idx is not None:
        region_values.append(ordered_by_value[default_idx].value)
        i = default_idx - 1
        while i >= 0 and (1 if ordered_by_value[i].total_return_percent >= 0 else -1) == default_sign:
            region_values.append(ordered_by_value[i].value)
            i -= 1
        i = default_idx + 1
        while i < len(ordered_by_value) and (1 if ordered_by_value[i].total_return_percent >= 0 else -1) == default_sign:
            region_values.append(ordered_by_value[i].value)
            i += 1

    if region_values:
        result.robust_region_min = min(region_values)
        result.robust_region_max = max(region_values)

    return result


def run_sensitivity_analysis(
    ticker: str,
    full_price_df: pd.DataFrame,
    start_date: dt.date,
    end_date: dt.date,
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
    model_version: str = MODEL_VERSION_CURRENT,
    parameters: tuple[str, ...] = THRESHOLD_PARAMETERS,
) -> SensitivityResult:
    results: list[ParameterSensitivity] = []

    for parameter in parameters:
        if parameter not in SENSITIVITY_RANGES:
            continue
        default_value = DEFAULT_VALUES[parameter]

        points = [
            _run_variant(
                ticker, full_price_df, start_date, end_date, initial_capital,
                transaction_cost_bps, slippage_bps, model_version,
                parameter, v, v == default_value,
                _thresholds_for(parameter, v), _indicator_params_for(parameter, v),
            )
            for v in SENSITIVITY_RANGES[parameter]
        ]
        results.append(_summarize(points, default_value))

    return SensitivityResult(ticker=ticker, model_version=model_version, parameters=results)


@dataclass
class HeatmapCell:
    x_value: float
    y_value: float
    metric_value: float | None
    number_of_trades: int
    insufficient_sample: bool


@dataclass
class SensitivityHeatmapResult:
    ticker: str
    param_x: str
    param_y: str
    metric: str
    cells: list[HeatmapCell] = field(default_factory=list)
    methodology: str = (
        "Each cell re-runs the full backtest with both parameters set to that cell's values, "
        "holding all others at their defaults. Cells with fewer than 5 trades are flagged "
        "insufficient_sample=true rather than colored as if they were reliable."
    )


def run_sensitivity_heatmap(
    ticker: str,
    full_price_df: pd.DataFrame,
    start_date: dt.date,
    end_date: dt.date,
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
    param_x: str,
    param_y: str,
    metric: str = "cagr_percent",
    model_version: str = MODEL_VERSION_CURRENT,
) -> SensitivityHeatmapResult:
    if param_x not in SENSITIVITY_RANGES or param_y not in SENSITIVITY_RANGES:
        raise ValueError(f"Unknown sensitivity parameter(s): {param_x}, {param_y}")

    cells: list[HeatmapCell] = []
    for x_val in SENSITIVITY_RANGES[param_x]:
        for y_val in SENSITIVITY_RANGES[param_y]:
            thresholds = ScoreThresholds()
            indicator_overrides: dict = {}
            for p, v in ((param_x, x_val), (param_y, y_val)):
                if p == "buy_threshold":
                    thresholds = ScoreThresholds(buy=v, sell_low=thresholds.sell_low)
                elif p == "sell_threshold":
                    thresholds = ScoreThresholds(buy=thresholds.buy, sell_low=v)
                else:
                    indicator_overrides[p] = int(v)

            indicator_params = IndicatorParams(**indicator_overrides)
            precomputed = None
            if indicator_overrides:
                precomputed = compute_custom_indicator_frame(full_price_df, indicator_params)

            try:
                result = run_backtest(
                    ticker=ticker, full_price_df=full_price_df, start_date=start_date, end_date=end_date,
                    initial_capital=initial_capital, transaction_cost_bps=transaction_cost_bps,
                    slippage_bps=slippage_bps, model_version=model_version, thresholds=thresholds,
                    precomputed_indicator_df=precomputed,
                )
                trades = result.trade_stats.get("number_of_trades", 0)
                metric_value = getattr(result, metric, None)
                if metric_value is None:
                    metric_value = result.advanced_metrics.get(metric)
                cells.append(
                    HeatmapCell(
                        x_value=x_val, y_value=y_val, metric_value=metric_value,
                        number_of_trades=trades, insufficient_sample=trades < MIN_TRADES_FOR_ROBUSTNESS_VERDICT,
                    )
                )
            except InsufficientHistoryError:
                cells.append(
                    HeatmapCell(x_value=x_val, y_value=y_val, metric_value=None, number_of_trades=0, insufficient_sample=True)
                )

    return SensitivityHeatmapResult(ticker=ticker, param_x=param_x, param_y=param_y, metric=metric, cells=cells)
