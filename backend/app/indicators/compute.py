"""Orchestrates all indicator calculations into one aligned DataFrame, plus
deterministic classification helpers (trend direction, volatility regime)
used by both the live signal engine and the backtester.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from app.config import (
    ATR_WINDOW,
    BOLLINGER_STD,
    BOLLINGER_WINDOW,
    EMA_WINDOWS,
    HIST_VOL_ANNUALIZATION,
    HIST_VOL_WINDOW,
    MACD_FAST,
    MACD_SIGNAL,
    MACD_SLOW,
    ROC_WINDOW,
    RSI_WINDOW,
    SMA_WINDOWS,
    VOLUME_SMA_WINDOW,
)
from app.indicators import momentum, trend, volatility
from app.indicators import volume as volume_ind


def compute_indicator_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Given an OHLCV DataFrame (columns: Open, High, Low, Close, Volume),
    return a new DataFrame with every indicator column appended, aligned by
    the same DatetimeIndex. Pure function: no mutation of the input.
    """
    out = df.copy()
    close = out["Close"]
    high = out["High"]
    low = out["Low"]
    vol = out["Volume"]

    for w in SMA_WINDOWS:
        out[f"SMA_{w}"] = trend.sma(close, w)
    for w in EMA_WINDOWS:
        out[f"EMA_{w}"] = trend.ema(close, w)

    out["RSI_14"] = momentum.rsi(close, RSI_WINDOW)

    macd_line, signal_line, hist = momentum.macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    out["MACD"] = macd_line
    out["MACD_SIGNAL"] = signal_line
    out["MACD_HIST"] = hist

    out["ROC_12"] = momentum.roc(close, ROC_WINDOW)

    out["ATR_14"] = volatility.atr(high, low, close, ATR_WINDOW)

    bb_upper, bb_middle, bb_lower = volatility.bollinger_bands(close, BOLLINGER_WINDOW, BOLLINGER_STD)
    out["BB_UPPER"] = bb_upper
    out["BB_MIDDLE"] = bb_middle
    out["BB_LOWER"] = bb_lower

    out["HIST_VOL_20"] = volatility.historical_volatility(close, HIST_VOL_WINDOW, HIST_VOL_ANNUALIZATION)

    out["VOLUME_SMA_20"] = volume_ind.volume_sma(vol, VOLUME_SMA_WINDOW)
    out["REL_VOLUME"] = volume_ind.relative_volume(vol, VOLUME_SMA_WINDOW)

    out["DIST_SMA_20_PCT"] = (close - out["SMA_20"]) / out["SMA_20"] * 100.0
    out["DIST_SMA_50_PCT"] = (close - out["SMA_50"]) / out["SMA_50"] * 100.0
    out["DIST_SMA_200_PCT"] = (close - out["SMA_200"]) / out["SMA_200"] * 100.0

    return out


def safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def row_to_dict(row: pd.Series, columns: list[str]) -> dict[str, float | None]:
    return {col: safe_float(row.get(col)) for col in columns}


TREND_CLASSES = ("Strong Bearish", "Bearish", "Neutral", "Bullish", "Strong Bullish")


def classify_trend(row: pd.Series) -> str:
    """Combines four directional comparisons into a -4..+4 score and maps it
    to a five-bucket trend classification. Returns 'Insufficient Data' if the
    long-window SMAs required for this classification aren't available yet.
    """
    close = safe_float(row.get("Close"))
    sma20 = safe_float(row.get("SMA_20"))
    sma50 = safe_float(row.get("SMA_50"))
    sma200 = safe_float(row.get("SMA_200"))

    if None in (close, sma20, sma50, sma200):
        return "Insufficient Data"

    score = 0
    score += 1 if close > sma20 else -1
    score += 1 if sma20 > sma50 else -1
    score += 1 if sma50 > sma200 else -1
    score += 1 if close > sma200 else -1

    if score >= 3:
        return "Strong Bullish"
    if score >= 1:
        return "Bullish"
    if score <= -3:
        return "Strong Bearish"
    if score <= -1:
        return "Bearish"
    return "Neutral"


VOLATILITY_REGIMES = ("Low", "Normal", "Elevated", "Extreme")


def classify_volatility_regime(indicator_df: pd.DataFrame, lookback: int = 252) -> str:
    """Ranks the latest annualized historical volatility against its own
    trailing distribution (percentile rank), so 'elevated' is relative to
    this specific stock's own recent behavior rather than a fixed number
    that means different things for a utility stock vs. a small-cap.
    """
    series = indicator_df["HIST_VOL_20"].dropna()
    if series.empty:
        return "Insufficient Data"

    window = series.tail(lookback)
    latest = window.iloc[-1]
    if len(window) < 20:
        return "Insufficient Data"

    percentile = (window <= latest).mean() * 100.0

    if percentile >= 90:
        return "Extreme"
    if percentile >= 75:
        return "Elevated"
    if percentile <= 25:
        return "Low"
    return "Normal"


INDICATOR_COLUMNS = [
    "Close",
    "SMA_20",
    "SMA_50",
    "SMA_100",
    "SMA_200",
    "EMA_20",
    "EMA_50",
    "RSI_14",
    "MACD",
    "MACD_SIGNAL",
    "MACD_HIST",
    "ROC_12",
    "ATR_14",
    "BB_UPPER",
    "BB_MIDDLE",
    "BB_LOWER",
    "HIST_VOL_20",
    "VOLUME_SMA_20",
    "REL_VOLUME",
    "DIST_SMA_20_PCT",
    "DIST_SMA_50_PCT",
    "DIST_SMA_200_PCT",
    "Volume",
]
