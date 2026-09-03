"""Model confidence: how much internal agreement and data quality backs the
signal - explicitly NOT a probability that the price will move in any
direction. See README "Confidence Methodology" for the full writeup.

confidence = weighted blend of:
  - completeness:      available factors / total possible factors
  - agreement:         share of non-neutral factors pointing the same way
                        as the overall score (bullish if score >= 50, else
                        bearish)
  - stability margin:  how far the score sits from the nearest signal
                        threshold boundary (a score sitting right on a
                        boundary is less stable than one deep in a bucket)
  - volatility clarity: extreme volatility regimes reduce confidence
"""
from __future__ import annotations

from dataclasses import dataclass

from app.signals.engine import SignalResult

# Total number of factors the engine could theoretically produce when all
# indicators have enough history (3 trend + 3 momentum + 1 volume + 1 volatility).
TOTAL_POSSIBLE_FACTORS = 8

SIGNAL_THRESHOLDS = (0.0, 30.0, 45.0, 65.0, 80.0, 100.0)

CONFIDENCE_METHODOLOGY = (
    "Model confidence reflects internal indicator agreement and data "
    "completeness; it is NOT the probability of future returns."
)


@dataclass
class ConfidenceResult:
    confidence_percent: float
    completeness: float
    agreement: float
    stability_margin: float
    volatility_clarity: float
    methodology: str = CONFIDENCE_METHODOLOGY


def _nearest_threshold_distance(score: float) -> float:
    return min(abs(score - t) for t in SIGNAL_THRESHOLDS)


def compute_confidence(result: SignalResult) -> ConfidenceResult:
    completeness = min(1.0, len(result.factors) / TOTAL_POSSIBLE_FACTORS)

    non_neutral = [f for f in result.factors if f.polarity != "neutral"]
    if non_neutral:
        leaning_bullish = result.score >= 50.0
        agreeing = [
            f
            for f in non_neutral
            if (f.polarity == "positive") == leaning_bullish
        ]
        agreement = len(agreeing) / len(non_neutral)
    else:
        agreement = 0.5

    # Max meaningful distance from a boundary is half the smallest bucket
    # width (15, from HOLD's 45-65 range); cap the margin there.
    stability_margin = min(1.0, _nearest_threshold_distance(result.score) / 10.0)

    volatility_penalty = {
        "Low": 0.0,
        "Normal": 0.0,
        "Elevated": 0.15,
        "Extreme": 0.35,
        "Insufficient Data": 0.20,
    }.get(result.volatility_regime, 0.20)
    volatility_clarity = 1.0 - volatility_penalty

    raw = (
        completeness * 0.30
        + agreement * 0.40
        + stability_margin * 0.15
        + volatility_clarity * 0.15
    )

    # Never claim absolute certainty in either direction.
    confidence_percent = round(max(5.0, min(97.0, raw * 100.0)), 1)

    return ConfidenceResult(
        confidence_percent=confidence_percent,
        completeness=round(completeness, 3),
        agreement=round(agreement, 3),
        stability_margin=round(stability_margin, 3),
        volatility_clarity=round(volatility_clarity, 3),
    )
