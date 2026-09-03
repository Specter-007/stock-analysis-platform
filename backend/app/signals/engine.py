"""Deterministic, rules-based BUY/HOLD/SELL scoring engine.

No machine learning, no LLM call, no randomness. Every factor below is a
plain comparison against the indicator values computed for the ticker's
actual retrieved price history. Given the same OHLCV input, `evaluate()`
always returns exactly the same output.

A BUY/SELL/HOLD label produced here means only: "this predefined rules-based
model, evaluated against the latest available daily candle, currently
classifies this ticker's technical state into this bucket." It is not a
prediction and not personalized financial advice.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.config import (
    MODEL_VERSION_CURRENT,
    RAW_SCORE_FIXED_MAX,
    RAW_SCORE_FIXED_MIN,
    SCORE_BUY,
    SCORE_HOLD_LOW,
    SCORE_SELL_LOW,
    SCORE_STRONG_BUY,
)
from app.indicators.compute import classify_trend, classify_volatility_regime, safe_float

Polarity = str  # "positive" | "negative" | "neutral"

CATEGORIES = ("Trend", "Momentum", "Volume", "Volatility")


@dataclass
class ScoreFactor:
    category: str  # "Trend" | "Momentum" | "Volume" | "Volatility"
    name: str
    points: float
    min_points: float
    max_points: float
    detail: str
    polarity: Polarity
    current_value: float | None = None
    threshold_label: str = ""


@dataclass
class SignalResult:
    signal: str  # STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL
    score: float  # normalized 0-100
    raw_score: float
    raw_min: float
    raw_max: float
    model_version: str = MODEL_VERSION_CURRENT
    factors: list[ScoreFactor] = field(default_factory=list)
    trend_classification: str = "Insufficient Data"
    volatility_regime: str = "Insufficient Data"

    @property
    def positive_factors(self) -> list[ScoreFactor]:
        return [f for f in self.factors if f.polarity == "positive"]

    @property
    def negative_factors(self) -> list[ScoreFactor]:
        return [f for f in self.factors if f.polarity == "negative"]

    @property
    def neutral_factors(self) -> list[ScoreFactor]:
        return [f for f in self.factors if f.polarity == "neutral"]

    @property
    def category_breakdown(self) -> dict[str, float]:
        """Sum of raw points contributed by each category, plus 'Other' for
        any factor category not in the standard four (keeps this forward
        compatible if a new category is ever added).
        """
        breakdown = {c: 0.0 for c in CATEGORIES}
        other = 0.0
        for f in self.factors:
            if f.category in breakdown:
                breakdown[f.category] += f.points
            else:
                other += f.points
        if other:
            breakdown["Other"] = other
        return breakdown


def _polarity(points: float) -> Polarity:
    if points > 0:
        return "positive"
    if points < 0:
        return "negative"
    return "neutral"


def _trend_factors(row: pd.Series) -> list[ScoreFactor]:
    close = safe_float(row.get("Close"))
    sma20 = safe_float(row.get("SMA_20"))
    sma50 = safe_float(row.get("SMA_50"))
    sma200 = safe_float(row.get("SMA_200"))

    factors: list[ScoreFactor] = []

    if close is not None and sma200 is not None:
        bullish = close > sma200
        pts = 15.0 if bullish else -15.0
        factors.append(
            ScoreFactor(
                category="Trend",
                name="Price vs. 200-day SMA",
                points=pts,
                min_points=-15,
                max_points=15,
                detail=(
                    f"Price (${close:.2f}) is {'above' if bullish else 'below'} "
                    f"the 200-day SMA (${sma200:.2f})."
                ),
                polarity=_polarity(pts),
                current_value=close,
                threshold_label=f"Price > SMA 200 (${sma200:.2f})",
            )
        )

    if sma50 is not None and sma200 is not None:
        bullish = sma50 > sma200
        pts = 15.0 if bullish else -15.0
        factors.append(
            ScoreFactor(
                category="Trend",
                name="50-day SMA vs. 200-day SMA",
                points=pts,
                min_points=-15,
                max_points=15,
                detail=(
                    f"50-day SMA (${sma50:.2f}) is {'above' if bullish else 'below'} "
                    f"the 200-day SMA (${sma200:.2f}) "
                    f"({'golden' if bullish else 'death'}-cross alignment)."
                ),
                polarity=_polarity(pts),
                current_value=sma50,
                threshold_label=f"SMA 50 > SMA 200 (${sma200:.2f})",
            )
        )

    if sma20 is not None and sma50 is not None:
        bullish = sma20 > sma50
        pts = 10.0 if bullish else -10.0
        factors.append(
            ScoreFactor(
                category="Trend",
                name="20-day SMA vs. 50-day SMA",
                points=pts,
                min_points=-10,
                max_points=10,
                detail=(
                    f"20-day SMA (${sma20:.2f}) is {'above' if bullish else 'below'} "
                    f"the 50-day SMA (${sma50:.2f})."
                ),
                polarity=_polarity(pts),
                current_value=sma20,
                threshold_label=f"SMA 20 > SMA 50 (${sma50:.2f})",
            )
        )

    return factors


def _rsi_factor(row: pd.Series) -> ScoreFactor | None:
    rsi = safe_float(row.get("RSI_14"))
    if rsi is None:
        return None

    if rsi > 70:
        pts, label = -5.0, "overbought (pullback risk)"
    elif rsi >= 50:
        pts, label = 10.0, "healthy bullish momentum"
    elif rsi >= 45:
        pts, label = 0.0, "neutral"
    elif rsi >= 30:
        pts, label = -5.0, "weakening / bearish momentum"
    else:
        pts, label = -10.0, "oversold (bearish momentum extreme)"

    return ScoreFactor(
        category="Momentum",
        name="RSI (14)",
        points=pts,
        min_points=-10,
        max_points=10,
        detail=f"RSI is {rsi:.1f} — {label}.",
        polarity=_polarity(pts),
        current_value=rsi,
        threshold_label="RSI 50-70 healthy bullish; >70 overbought; <30 oversold",
    )


def _macd_factor(row: pd.Series) -> ScoreFactor | None:
    macd_line = safe_float(row.get("MACD"))
    signal_line = safe_float(row.get("MACD_SIGNAL"))
    if macd_line is None or signal_line is None:
        return None

    above_signal = macd_line > signal_line
    above_zero = macd_line > 0

    if above_signal and above_zero:
        pts, label = 15.0, "strong bullish (above signal line and above zero)"
    elif above_signal and not above_zero:
        pts, label = 8.0, "bullish crossover, still below zero"
    elif not above_signal and above_zero:
        pts, label = -8.0, "bearish crossover, still above zero"
    else:
        pts, label = -15.0, "strong bearish (below signal line and below zero)"

    return ScoreFactor(
        category="Momentum",
        name="MACD",
        points=pts,
        min_points=-15,
        max_points=15,
        detail=f"MACD ({macd_line:.2f}) vs. signal ({signal_line:.2f}): {label}.",
        polarity=_polarity(pts),
        current_value=macd_line,
        threshold_label=f"MACD > signal ({signal_line:.2f}) and MACD > 0",
    )


def _roc_factor(row: pd.Series) -> ScoreFactor | None:
    roc = safe_float(row.get("ROC_12"))
    if roc is None:
        return None

    if roc > 1.0:
        pts = 5.0
    elif roc < -1.0:
        pts = -5.0
    else:
        pts = 0.0

    return ScoreFactor(
        category="Momentum",
        name="Rate of Change (12)",
        points=pts,
        min_points=-5,
        max_points=5,
        detail=f"12-period ROC is {roc:+.2f}%.",
        polarity=_polarity(pts),
        current_value=roc,
        threshold_label="ROC > +1% bullish; < -1% bearish",
    )


def _volume_factor(indicator_df: pd.DataFrame) -> ScoreFactor | None:
    if len(indicator_df) < 2:
        return None
    row = indicator_df.iloc[-1]
    prev_close = safe_float(indicator_df.iloc[-2].get("Close"))
    close = safe_float(row.get("Close"))
    rel_vol = safe_float(row.get("REL_VOLUME"))
    if None in (prev_close, close, rel_vol):
        return None

    daily_return_pct = (close - prev_close) / prev_close * 100 if prev_close else 0.0
    above_avg = rel_vol > 1.2

    if above_avg and daily_return_pct > 0:
        pts, label = 10.0, "bullish move confirmed by above-average volume"
    elif above_avg and daily_return_pct < 0:
        pts, label = -10.0, "bearish move confirmed by above-average volume"
    else:
        pts, label = 0.0, "volume in line with average, no strong confirmation"

    return ScoreFactor(
        category="Volume",
        name="Volume confirmation",
        points=pts,
        min_points=-10,
        max_points=10,
        detail=(
            f"Relative volume {rel_vol:.2f}x average with a {daily_return_pct:+.2f}% "
            f"daily move — {label}."
        ),
        polarity=_polarity(pts),
        current_value=rel_vol,
        threshold_label="Relative volume > 1.2x average, confirming the day's price direction",
    )


def _volatility_factor(indicator_df: pd.DataFrame, regime: str) -> ScoreFactor | None:
    if regime == "Insufficient Data":
        return None

    mapping = {
        "Low": (5.0, "low relative to its own trailing history"),
        "Normal": (5.0, "within its normal trailing range"),
        "Elevated": (-5.0, "elevated relative to its own trailing history"),
        "Extreme": (-10.0, "extreme relative to its own trailing history"),
    }
    pts, label = mapping[regime]

    return ScoreFactor(
        category="Volatility",
        name="Volatility regime",
        points=pts,
        min_points=-10,
        max_points=5,
        detail=f"Volatility regime is {regime} — {label}.",
        polarity=_polarity(pts),
        current_value=None,
        threshold_label="Low/Normal regime rewarded; Elevated/Extreme penalized",
    )


@dataclass
class ScoreThresholds:
    """Defaults to the standard, versioned thresholds from config. A caller
    (currently only parameter-sensitivity analysis) may override these to
    test a perturbed model - any such run must be labeled a CUSTOM model in
    the API/UI, never presented as a standard versioned result.
    """

    strong_buy: float = SCORE_STRONG_BUY
    buy: float = SCORE_BUY
    hold_low: float = SCORE_HOLD_LOW
    sell_low: float = SCORE_SELL_LOW


DEFAULT_THRESHOLDS = ScoreThresholds()


def score_to_signal(score: float, thresholds: ScoreThresholds = DEFAULT_THRESHOLDS) -> str:
    if score >= thresholds.strong_buy:
        return "STRONG_BUY"
    if score >= thresholds.buy:
        return "BUY"
    if score >= thresholds.hold_low:
        return "HOLD"
    if score >= thresholds.sell_low:
        return "SELL"
    return "STRONG_SELL"


def evaluate(
    indicator_df: pd.DataFrame,
    model_version: str = MODEL_VERSION_CURRENT,
    thresholds: ScoreThresholds = DEFAULT_THRESHOLDS,
) -> SignalResult:
    """Evaluate the deterministic signal at the LAST row of `indicator_df`.

    `indicator_df` must already contain the columns produced by
    `app.indicators.compute.compute_indicator_frame`. The caller is
    responsible for ensuring the frame contains no data from after the
    evaluation point (critical for backtesting - see backtesting/engine.py).

    `model_version`:
      - "1.1" (default) - raw score normalized against the FIXED theoretical
        min/max across all 8 possible factors. The same factor condition
        contributes the same normalized amount for every ticker.
      - "1.0" (legacy) - raw score normalized against the min/max of only
        the factors available for THIS ticker. Kept for backward-compatible
        reference; never silently substituted for v1.1 results.
    """
    if indicator_df.empty:
        raise ValueError("Cannot evaluate signal on an empty indicator frame.")

    row = indicator_df.iloc[-1]

    factors: list[ScoreFactor] = []
    factors.extend(_trend_factors(row))

    for f in (_rsi_factor(row), _macd_factor(row), _roc_factor(row)):
        if f is not None:
            factors.append(f)

    vol_factor = _volume_factor(indicator_df)
    if vol_factor is not None:
        factors.append(vol_factor)

    regime = classify_volatility_regime(indicator_df)
    volat_factor = _volatility_factor(indicator_df, regime)
    if volat_factor is not None:
        factors.append(volat_factor)

    raw_score = sum(f.points for f in factors)

    if model_version == "1.0":
        raw_min = sum(f.min_points for f in factors)
        raw_max = sum(f.max_points for f in factors)
    else:
        raw_min = RAW_SCORE_FIXED_MIN
        raw_max = RAW_SCORE_FIXED_MAX

    if raw_max == raw_min:
        normalized = 50.0
    else:
        normalized = (raw_score - raw_min) / (raw_max - raw_min) * 100.0
        normalized = max(0.0, min(100.0, normalized))

    return SignalResult(
        signal=score_to_signal(normalized, thresholds),
        score=round(normalized, 1),
        raw_score=raw_score,
        raw_min=raw_min,
        raw_max=raw_max,
        model_version=model_version,
        factors=factors,
        trend_classification=classify_trend(row),
        volatility_regime=regime,
    )
