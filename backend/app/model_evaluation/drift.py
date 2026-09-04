"""V5: model drift monitoring.

Compares a RECENT window of trading sessions against the HISTORICAL
baseline that precedes it (both drawn from the same signal-history
computation already used by the Model Performance page) across three
dimensions: signal-class distribution, factor-category contribution mix,
and market-regime distribution. Every number here is a real recomputation
of the same deterministic signal engine / regime classifier used everywhere
else in this app - nothing is estimated or invented for this module.

Detection methodology is a documented, transparent PERCENTAGE-POINT
THRESHOLD (`DRIFT_SIGNIFICANT_SHIFT_PP`), not a formal hypothesis test:
daily signals and regimes are highly autocorrelated (a signal or a regime
typically persists across many consecutive days), so a classical test that
assumes independent observations (e.g. a chi-square goodness-of-fit test)
would systematically overstate its own significance here. A plain,
disclosed threshold is more statistically honest than a p-value that
doesn't mean what a reader would assume it means.

Detecting drift never changes model weights, thresholds, or version - it
only reports what changed, for the user to decide what research to run next.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.config import (
    DRIFT_MIN_SESSIONS_FOR_COMPARISON,
    DRIFT_RECENT_WINDOW_SESSIONS,
    DRIFT_SIGNIFICANT_SHIFT_PP,
    MODEL_VERSION_CURRENT,
    SIGNAL_PERFORMANCE_LOOKBACK_SESSIONS,
)
from app.indicators.compute import compute_indicator_frame
from app.market.regime import classify_market_regime
from app.signals import history as history_module
from app.signals.engine import CATEGORIES, SignalResult

DRIFT_METHODOLOGY = (
    f"Compares the most recent {DRIFT_RECENT_WINDOW_SESSIONS} trading sessions against the "
    "historical sessions that precede them (same signal-history computation as the Model "
    "Performance page - every point is a real, causally-computed signal, never estimated). A "
    f"bucket is flagged only when its share moved by at least {DRIFT_SIGNIFICANT_SHIFT_PP:.0f} "
    "percentage points between the two windows - a documented, transparent threshold heuristic, "
    "not a formal hypothesis test. Daily signals and regimes are highly autocorrelated (a signal "
    "or regime typically persists across many consecutive days), so a classical significance test "
    "assuming independent observations would overstate its own confidence here. Detecting drift "
    "never changes model weights, thresholds, or version on its own."
)

_SIGNAL_BUCKETS = {
    "STRONG_BUY": "BUY", "BUY": "BUY",
    "HOLD": "HOLD",
    "SELL": "SELL", "STRONG_SELL": "SELL",
}
_BUCKET_ORDER = ("BUY", "HOLD", "SELL")


@dataclass
class DistributionComparison:
    dimension: str  # "signal" | "factor" | "regime"
    historical_percent: dict[str, float]
    recent_percent: dict[str, float]
    shifted_buckets: list[str] = field(default_factory=list)
    flagged: bool = False


@dataclass
class ModelDriftResult:
    ticker: str
    model_version: str
    historical_sessions: int
    recent_sessions: int
    insufficient_data: bool
    signal_distribution: DistributionComparison | None = None
    factor_distribution: DistributionComparison | None = None
    regime_distribution: DistributionComparison | None = None
    methodology: str = DRIFT_METHODOLOGY


def _bucketed_signal_distribution(points: list[history_module.SignalHistoryPoint]) -> dict[str, float]:
    if not points:
        return {b: 0.0 for b in _BUCKET_ORDER}
    counts = {b: 0 for b in _BUCKET_ORDER}
    for p in points:
        counts[_SIGNAL_BUCKETS.get(p.signal, "HOLD")] += 1
    total = len(points)
    return {b: round(c / total * 100.0, 1) for b, c in counts.items()}


def _factor_distribution(results: list[SignalResult]) -> dict[str, float]:
    if not results:
        return {c: 0.0 for c in CATEGORIES}
    totals = {c: 0.0 for c in CATEGORIES}
    for r in results:
        breakdown = r.category_breakdown
        for c in CATEGORIES:
            totals[c] += abs(breakdown.get(c, 0.0))
    grand_total = sum(totals.values())
    if grand_total <= 0:
        return {c: 0.0 for c in CATEGORIES}
    return {c: round(v / grand_total * 100.0, 1) for c, v in totals.items()}


def _regime_distribution(benchmark: str, benchmark_indicator_df: pd.DataFrame, dates: list) -> dict[str, str]:
    date_to_position = {ts.date(): i for i, ts in enumerate(benchmark_indicator_df.index)}
    out: dict = {}
    for date in dates:
        pos = date_to_position.get(date)
        if pos is None:
            out[date] = "UNAVAILABLE"
            continue
        sliced = benchmark_indicator_df.iloc[: pos + 1]
        out[date] = classify_market_regime(benchmark, sliced).regime
    return out


def _regime_bucket_percent(regimes: list[str]) -> dict[str, float]:
    if not regimes:
        return {}
    counts: dict[str, int] = {}
    for r in regimes:
        counts[r] = counts.get(r, 0) + 1
    total = len(regimes)
    return {r: round(c / total * 100.0, 1) for r, c in counts.items()}


def _compare(dimension: str, historical: dict[str, float], recent: dict[str, float]) -> DistributionComparison:
    all_buckets = set(historical) | set(recent)
    shifted = [
        b for b in all_buckets
        if abs(recent.get(b, 0.0) - historical.get(b, 0.0)) >= DRIFT_SIGNIFICANT_SHIFT_PP
    ]
    return DistributionComparison(
        dimension=dimension,
        historical_percent=historical,
        recent_percent=recent,
        shifted_buckets=sorted(shifted),
        flagged=len(shifted) > 0,
    )


def detect_model_drift(
    ticker: str,
    full_price_df: pd.DataFrame,
    benchmark: str,
    benchmark_full_price_df: pd.DataFrame,
    model_version: str = MODEL_VERSION_CURRENT,
    lookback_sessions: int = SIGNAL_PERFORMANCE_LOOKBACK_SESSIONS,
    recent_window: int = DRIFT_RECENT_WINDOW_SESSIONS,
) -> ModelDriftResult:
    indicator_df = compute_indicator_frame(full_price_df)
    full_history = history_module.compute_signal_history_full(indicator_df, lookback_sessions, model_version)

    total_sessions = len(full_history)
    historical_sessions = max(0, total_sessions - recent_window)
    recent_sessions = min(recent_window, total_sessions)

    if historical_sessions < DRIFT_MIN_SESSIONS_FOR_COMPARISON or recent_sessions < DRIFT_MIN_SESSIONS_FOR_COMPARISON:
        return ModelDriftResult(
            ticker=ticker, model_version=model_version,
            historical_sessions=historical_sessions, recent_sessions=recent_sessions,
            insufficient_data=True,
        )

    historical_entries = full_history[:historical_sessions]
    recent_entries = full_history[historical_sessions:]

    historical_points = [history_module.SignalHistoryPoint(date=d, signal=r.signal, score=r.score, model_version=r.model_version) for d, r in historical_entries]
    recent_points = [history_module.SignalHistoryPoint(date=d, signal=r.signal, score=r.score, model_version=r.model_version) for d, r in recent_entries]

    signal_comparison = _compare(
        "signal",
        _bucketed_signal_distribution(historical_points),
        _bucketed_signal_distribution(recent_points),
    )

    historical_results = [r for _, r in historical_entries]
    recent_results = [r for _, r in recent_entries]
    factor_comparison = _compare(
        "factor",
        _factor_distribution(historical_results),
        _factor_distribution(recent_results),
    )

    benchmark_indicator_df = compute_indicator_frame(benchmark_full_price_df)
    all_dates = [pd.Timestamp(d).date() for d, _ in full_history]
    regime_by_date = _regime_distribution(benchmark, benchmark_indicator_df, all_dates)
    historical_regimes = [regime_by_date[pd.Timestamp(d).date()] for d, _ in historical_entries]
    recent_regimes = [regime_by_date[pd.Timestamp(d).date()] for d, _ in recent_entries]
    regime_comparison = _compare(
        "regime",
        _regime_bucket_percent(historical_regimes),
        _regime_bucket_percent(recent_regimes),
    )

    return ModelDriftResult(
        ticker=ticker,
        model_version=model_version,
        historical_sessions=historical_sessions,
        recent_sessions=recent_sessions,
        insufficient_data=False,
        signal_distribution=signal_comparison,
        factor_distribution=factor_comparison,
        regime_distribution=regime_comparison,
    )
