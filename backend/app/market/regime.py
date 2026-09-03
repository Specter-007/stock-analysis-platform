"""Deterministic market-regime classification, based on a major benchmark
(default SPY). No machine learning - reuses the same causal trend and
volatility-regime classifiers used for individual stocks, applied to the
benchmark's own price history.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.indicators.compute import classify_trend, classify_volatility_regime, safe_float

REGIME_LABELS = ("BULL", "BEAR", "SIDEWAYS", "HIGH_VOLATILITY", "UNAVAILABLE")


@dataclass
class MarketRegimeResult:
    benchmark: str
    regime: str
    trend_classification: str
    momentum: str  # "Positive" | "Negative" | "Neutral"
    volatility_regime: str
    regime_confidence_percent: float
    methodology: str = (
        "Deterministic classification from the benchmark's own trend (price vs. "
        "SMA20/50/200) and volatility-regime (percentile of trailing historical "
        "volatility) indicators. An Extreme volatility regime overrides the trend "
        "label, since extreme volatility is usually the dominant characteristic of "
        "that period regardless of direction. Regime confidence reflects internal "
        "indicator agreement, NOT a probability of future market direction."
    )


def classify_market_regime(benchmark: str, indicator_df: pd.DataFrame) -> MarketRegimeResult:
    if indicator_df.empty:
        return MarketRegimeResult(
            benchmark=benchmark,
            regime="UNAVAILABLE",
            trend_classification="Insufficient Data",
            momentum="Neutral",
            volatility_regime="Insufficient Data",
            regime_confidence_percent=0.0,
        )

    row = indicator_df.iloc[-1]
    trend = classify_trend(row)
    vol_regime = classify_volatility_regime(indicator_df)
    roc = safe_float(row.get("ROC_12"))

    if roc is None:
        momentum = "Neutral"
    elif roc > 0.5:
        momentum = "Positive"
    elif roc < -0.5:
        momentum = "Negative"
    else:
        momentum = "Neutral"

    if vol_regime == "Extreme":
        regime = "HIGH_VOLATILITY"
    elif trend in ("Strong Bullish", "Bullish"):
        regime = "BULL"
    elif trend in ("Strong Bearish", "Bearish"):
        regime = "BEAR"
    elif trend == "Neutral":
        regime = "SIDEWAYS"
    else:
        regime = "UNAVAILABLE"

    trend_agreement = {
        "Strong Bullish": 1.0,
        "Strong Bearish": 1.0,
        "Bullish": 0.7,
        "Bearish": 0.7,
        "Neutral": 0.45,
        "Insufficient Data": 0.2,
    }.get(trend, 0.2)
    volatility_clarity = {
        "Low": 1.0,
        "Normal": 0.9,
        "Elevated": 0.6,
        "Extreme": 0.35,
        "Insufficient Data": 0.3,
    }.get(vol_regime, 0.3)

    confidence = round(max(20.0, min(97.0, (trend_agreement * 0.6 + volatility_clarity * 0.4) * 100)), 1)

    return MarketRegimeResult(
        benchmark=benchmark,
        regime=regime,
        trend_classification=trend,
        momentum=momentum,
        volatility_regime=vol_regime,
        regime_confidence_percent=confidence,
    )
