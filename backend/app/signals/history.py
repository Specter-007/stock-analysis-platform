"""Historical signal computation, change detection, and stability analysis.

Every historical signal here is computed the same way a live signal would
have been computed on that day: `signals.engine.evaluate()` is called on the
indicator frame truncated to end at that date, so no future information can
leak into a historical point (see `app.signals.engine` and
`app.backtesting.engine` for the same causal-truncation contract).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.config import (
    MODEL_VERSION_CURRENT,
    SIGNAL_HISTORY_LOOKBACK_SESSIONS,
    SIGNAL_STABILITY_WINDOW,
)
from app.signals import engine as signal_engine
from app.signals.engine import SignalResult


@dataclass
class SignalHistoryPoint:
    date: str
    signal: str
    score: float
    model_version: str


@dataclass
class SignalChange:
    date: str
    previous_signal: str
    current_signal: str
    previous_score: float
    current_score: float
    contributing_changes: list[str] = field(default_factory=list)


def compute_signal_history_full(
    indicator_df: pd.DataFrame,
    lookback_sessions: int = SIGNAL_HISTORY_LOOKBACK_SESSIONS,
    model_version: str = MODEL_VERSION_CURRENT,
) -> list[tuple[str, SignalResult]]:
    """Returns (date_str, full SignalResult) for each trading day in the last
    `lookback_sessions` days, oldest first. Days without enough warmup
    history to evaluate at all are simply omitted (never filled with a
    guessed value). Each day's result is computed from an indicator frame
    truncated to end at that day - identical to what a live signal on that
    day would have produced.
    """
    if indicator_df.empty:
        return []

    dates = indicator_df.index[-lookback_sessions:]
    out: list[tuple[str, SignalResult]] = []

    for date in dates:
        sliced = indicator_df.loc[:date]
        try:
            result = signal_engine.evaluate(sliced, model_version=model_version)
        except ValueError:
            continue
        out.append((str(date.date()), result))

    return out


def to_history_points(full_history: list[tuple[str, SignalResult]]) -> list[SignalHistoryPoint]:
    return [
        SignalHistoryPoint(date=d, signal=r.signal, score=r.score, model_version=r.model_version)
        for d, r in full_history
    ]


def compute_signal_history(
    indicator_df: pd.DataFrame,
    lookback_sessions: int = SIGNAL_HISTORY_LOOKBACK_SESSIONS,
    model_version: str = MODEL_VERSION_CURRENT,
) -> list[SignalHistoryPoint]:
    return to_history_points(compute_signal_history_full(indicator_df, lookback_sessions, model_version))


def detect_signal_change(full_history: list[tuple[str, SignalResult]]) -> SignalChange | None:
    """Compares the two most recent entries in `full_history`. Returns None
    if there's no change, or fewer than 2 entries to compare.
    """
    if len(full_history) < 2:
        return None

    (prev_date, prev_result), (curr_date, curr_result) = full_history[-2], full_history[-1]
    if prev_result.signal == curr_result.signal:
        return None

    contributing: list[str] = []
    prev_by_name = {f.name: f for f in prev_result.factors}
    for f in curr_result.factors:
        prior = prev_by_name.get(f.name)
        if prior is None or prior.polarity != f.polarity:
            if f.polarity == "positive":
                contributing.append(f"{f.name} turned bullish ({f.detail})")
            elif f.polarity == "negative":
                contributing.append(f"{f.name} turned bearish ({f.detail})")

    return SignalChange(
        date=curr_date,
        previous_signal=prev_result.signal,
        current_signal=curr_result.signal,
        previous_score=prev_result.score,
        current_score=curr_result.score,
        contributing_changes=contributing,
    )


def compute_signal_stability(history: list[SignalHistoryPoint], window: int = SIGNAL_STABILITY_WINDOW) -> tuple[float, list[str]]:
    """Stability = share of the most recent `window` sessions whose signal
    matches the LATEST session's signal. Returns (stability_percent, recent_signals)
    with recent_signals ordered most-recent-first (for display).

    This measures consistency of the model's own output over time - it is
    explicitly NOT a probability of any future return.
    """
    if not history:
        return 0.0, []

    recent = history[-window:]
    latest_signal = recent[-1].signal
    matches = sum(1 for p in recent if p.signal == latest_signal)
    stability = round(matches / len(recent) * 100, 1)
    recent_signals = [p.signal for p in reversed(recent)]
    return stability, recent_signals
