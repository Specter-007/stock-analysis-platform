"""Small numerical helpers shared by the risk panel and the backtester so
the same drawdown math is never duplicated (and can't silently drift apart).
"""
from __future__ import annotations

import pandas as pd


def running_max_drawdown_series(equity: pd.Series) -> pd.Series:
    """Drawdown at every point, as a negative fraction (e.g. -0.12 = -12%)."""
    running_peak = equity.cummax()
    return (equity - running_peak) / running_peak


def max_drawdown(equity: pd.Series) -> float | None:
    """Maximum peak-to-trough drawdown over the series, as a negative
    fraction. Returns None if there are fewer than 2 points.
    """
    if equity is None or len(equity) < 2:
        return None
    dd = running_max_drawdown_series(equity)
    return float(dd.min())
