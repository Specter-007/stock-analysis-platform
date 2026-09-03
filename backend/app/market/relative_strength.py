"""Relative-strength comparison against a benchmark (or peer), computed from
real historical closing prices over several fixed lookback windows.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.config import (
    RELATIVE_STRENGTH_PERIODS,
    RELATIVE_STRENGTH_STRONG_THRESHOLD_PP,
    RELATIVE_STRENGTH_WEAK_THRESHOLD_PP,
)
from app.indicators.compute import safe_float

RS_CLASSIFICATIONS = ("STRONG", "IN_LINE", "WEAK", "UNAVAILABLE")


@dataclass
class RelativeStrengthPeriod:
    period: str
    ticker_return_percent: float | None
    benchmark_return_percent: float | None
    relative_return_pp: float | None  # percentage-point difference
    classification: str


def period_return(close: pd.Series, sessions: int) -> float | None:
    if len(close) <= sessions:
        return None
    start = safe_float(close.iloc[-1 - sessions])
    end = safe_float(close.iloc[-1])
    if start is None or end is None or start == 0:
        return None
    return (end / start - 1.0) * 100.0


def _classify(relative_pp: float | None) -> str:
    if relative_pp is None:
        return "UNAVAILABLE"
    if relative_pp >= RELATIVE_STRENGTH_STRONG_THRESHOLD_PP:
        return "STRONG"
    if relative_pp <= RELATIVE_STRENGTH_WEAK_THRESHOLD_PP:
        return "WEAK"
    return "IN_LINE"


def compute_relative_strength(
    ticker_close: pd.Series, benchmark_close: pd.Series
) -> list[RelativeStrengthPeriod]:
    results = []
    for label, sessions in RELATIVE_STRENGTH_PERIODS.items():
        t_ret = period_return(ticker_close, sessions)
        b_ret = period_return(benchmark_close, sessions)
        relative = (t_ret - b_ret) if (t_ret is not None and b_ret is not None) else None
        results.append(
            RelativeStrengthPeriod(
                period=label,
                ticker_return_percent=round(t_ret, 2) if t_ret is not None else None,
                benchmark_return_percent=round(b_ret, 2) if b_ret is not None else None,
                relative_return_pp=round(relative, 2) if relative is not None else None,
                classification=_classify(relative),
            )
        )
    return results
