"""Parameter sensitivity analysis - the primary tool for detecting overfitting.

Perturbs the two decision-boundary parameters (the BUY and SELL score
thresholds) around their default values, one at a time, and re-runs the
SAME backtest engine for each variant. The question this answers is never
"what is the best threshold?" - it is "does performance hold up in the
neighborhood of the chosen threshold, or does it collapse a few points away
in either direction?" A model whose backtest only looks good at one exact
threshold value is a strong overfitting warning sign.

Scope note: only the BUY/SELL score thresholds are perturbed here (not
indicator periods like RSI/SMA/MACD windows, which would require a much
deeper refactor of the indicator-computation pipeline to parameterize).
This is a documented, intentional scope limit - see README.
"""
from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass, field

import pandas as pd

from app.backtesting.engine import run_backtest
from app.config import MODEL_VERSION_CURRENT, SCORE_BUY, SCORE_HOLD_LOW, SCORE_SELL_LOW, SCORE_STRONG_BUY
from app.services.exceptions import InsufficientHistoryError
from app.signals.engine import DEFAULT_THRESHOLDS, ScoreThresholds

BUY_THRESHOLD_RANGE = [55, 60, 65, 70, 75]
SELL_THRESHOLD_RANGE = [20, 25, 30, 35, 40]

ROBUSTNESS_METHODOLOGY = (
    "For each parameter, the coefficient of variation (std / |mean|) of total return across "
    "all tested values is computed. CV < 0.5 is labeled HIGHER_ROBUSTNESS (performance is "
    "reasonably stable across the neighborhood); CV >= 0.5, or a sign flip in the return, is "
    "labeled LOW_ROBUSTNESS. The 'robust region' is the longest contiguous run of tested values "
    "(including the default) whose return keeps the same sign as the default's return. This is a "
    "documented heuristic, not a statistical significance test."
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
    default_value: float
    points: list[SensitivityPoint] = field(default_factory=list)
    # HIGHER_ROBUSTNESS | LOW_ROBUSTNESS | INSUFFICIENT_DATA | PARAMETER_INERT
    robustness: str = "INSUFFICIENT_DATA"
    robust_region_min: float | None = None
    robust_region_max: float | None = None
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
    thresholds: ScoreThresholds,
    parameter: str,
    value: float,
    is_default: bool,
) -> SensitivityPoint:
    try:
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
            parameter=parameter,
            value=value,
            is_default=is_default,
            total_return_percent=None,
            cagr_percent=None,
            sharpe_ratio=None,
            max_drawdown_percent=None,
            number_of_trades=0,
        )


def _robust_region(
    points: list[SensitivityPoint], default_value: float
) -> tuple[str, float | None, float | None, str | None]:
    valid = [p for p in points if p.total_return_percent is not None]
    if len(valid) < 3:
        return "INSUFFICIENT_DATA", None, None, None

    returns = [p.total_return_percent for p in valid]
    mean_r = statistics.mean(returns)
    std_r = statistics.pstdev(returns)

    if std_r == 0:
        # Every tested value produced an IDENTICAL result. For this long/flat
        # engine, entry/exit only checks "is the signal BUY-class?" - so a
        # parameter that doesn't touch that boundary (e.g. the SELL/STRONG_SELL
        # split) cannot change a single trade, no matter how far it's moved.
        # Reporting this as "robust" would be misleading: it isn't stable
        # performance, it's a parameter with no behavioral effect at all.
        return (
            "PARAMETER_INERT",
            min(p.value for p in valid),
            max(p.value for p in valid),
            (
                "Every tested value produced an identical backtest result. This parameter does not "
                "affect the long/flat engine's entry/exit decision (which only checks whether the "
                "signal is BUY-class), so its 'robustness' here reflects having no effect, not stable "
                "performance."
            ),
        )

    cv = (std_r / abs(mean_r)) if mean_r != 0 else float("inf")

    default_point = next((p for p in points if p.is_default), None)
    default_sign = 1 if (default_point and (default_point.total_return_percent or 0) >= 0) else -1

    # Longest contiguous run (in parameter-value order) sharing the default's return sign.
    ordered = sorted(valid, key=lambda p: p.value)
    default_idx = next((i for i, p in enumerate(ordered) if p.is_default), None)

    region_values: list[float] = []
    if default_idx is not None:
        region_values.append(ordered[default_idx].value)
        i = default_idx - 1
        while i >= 0 and (1 if ordered[i].total_return_percent >= 0 else -1) == default_sign:
            region_values.append(ordered[i].value)
            i -= 1
        i = default_idx + 1
        while i < len(ordered) and (1 if ordered[i].total_return_percent >= 0 else -1) == default_sign:
            region_values.append(ordered[i].value)
            i += 1

    robustness = "HIGHER_ROBUSTNESS" if cv < 0.5 else "LOW_ROBUSTNESS"
    if not region_values:
        return robustness, None, None, None
    return robustness, min(region_values), max(region_values), None


def run_sensitivity_analysis(
    ticker: str,
    full_price_df: pd.DataFrame,
    start_date: dt.date,
    end_date: dt.date,
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
    model_version: str = MODEL_VERSION_CURRENT,
) -> SensitivityResult:
    parameters: list[ParameterSensitivity] = []

    buy_points = [
        _run_variant(
            ticker, full_price_df, start_date, end_date, initial_capital, transaction_cost_bps,
            slippage_bps, model_version,
            ScoreThresholds(strong_buy=SCORE_STRONG_BUY, buy=v, hold_low=SCORE_HOLD_LOW, sell_low=SCORE_SELL_LOW),
            "buy_threshold", v, v == SCORE_BUY,
        )
        for v in BUY_THRESHOLD_RANGE
    ]
    buy_robustness, buy_min, buy_max, buy_note = _robust_region(buy_points, SCORE_BUY)
    parameters.append(
        ParameterSensitivity(
            parameter="buy_threshold",
            default_value=SCORE_BUY,
            points=buy_points,
            robustness=buy_robustness,
            robust_region_min=buy_min,
            robust_region_max=buy_max,
            note=buy_note,
        )
    )

    sell_points = [
        _run_variant(
            ticker, full_price_df, start_date, end_date, initial_capital, transaction_cost_bps,
            slippage_bps, model_version,
            ScoreThresholds(strong_buy=SCORE_STRONG_BUY, buy=SCORE_BUY, hold_low=SCORE_HOLD_LOW, sell_low=v),
            "sell_threshold", v, v == SCORE_SELL_LOW,
        )
        for v in SELL_THRESHOLD_RANGE
    ]
    sell_robustness, sell_min, sell_max, sell_note = _robust_region(sell_points, SCORE_SELL_LOW)
    parameters.append(
        ParameterSensitivity(
            parameter="sell_threshold",
            default_value=SCORE_SELL_LOW,
            points=sell_points,
            robustness=sell_robustness,
            robust_region_min=sell_min,
            robust_region_max=sell_max,
            note=sell_note,
        )
    )

    return SensitivityResult(ticker=ticker, model_version=model_version, parameters=parameters)
