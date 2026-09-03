"""Deterministic, transparent fundamental score - entirely optional and
computed only when explicitly requested (see the `include_fundamental_score`
query flag on `/api/stock/{ticker}/signal`). It is never silently blended
into the core technical signal.

Methodology (documented, not hidden):
  Each of the metrics below contributes up to a fixed number of points if
  the metric is available AND falls in a "healthy" range for that metric.
  A metric that is unavailable for a ticker is excluded from both the score
  and its normalization range - never estimated or defaulted.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.fundamentals.service import FundamentalsResult

# (key, points_if_healthy, healthy_check)
_RULES: list[tuple[str, float, "callable"]] = [
    ("trailing_pe", 10.0, lambda v: 0 < v < 30),
    ("peg_ratio", 10.0, lambda v: 0 < v < 2.0),
    ("price_to_book", 5.0, lambda v: 0 < v < 8),
    ("revenue_growth", 15.0, lambda v: v > 5.0),
    ("earnings_growth", 15.0, lambda v: v > 5.0),
    ("profit_margin", 15.0, lambda v: v > 10.0),
    ("operating_margin", 10.0, lambda v: v > 10.0),
    ("return_on_equity", 10.0, lambda v: v > 10.0),
    ("debt_to_equity", 5.0, lambda v: v < 150.0),
    ("current_ratio", 5.0, lambda v: v > 1.0),
]


@dataclass
class FundamentalScoreFactor:
    key: str
    label: str
    value: float | None
    healthy: bool | None  # None when unavailable
    points: float
    max_points: float


@dataclass
class FundamentalScoreResult:
    score: float | None  # 0-100, None if no metrics were available at all
    factors: list[FundamentalScoreFactor] = field(default_factory=list)
    methodology: str = (
        "Sum of points for metrics currently in a 'healthy' range (fixed thresholds "
        "per metric), normalized against the max points of only the metrics Yahoo "
        "Finance actually reported for this ticker. A ticker missing several fields "
        "is scored fairly on the metrics it does have, never penalized for missing data."
    )


_LABELS = {
    "trailing_pe": "Trailing P/E",
    "peg_ratio": "PEG Ratio",
    "price_to_book": "Price / Book",
    "revenue_growth": "Revenue Growth",
    "earnings_growth": "Earnings Growth",
    "profit_margin": "Profit Margin",
    "operating_margin": "Operating Margin",
    "return_on_equity": "Return on Equity",
    "debt_to_equity": "Debt / Equity",
    "current_ratio": "Current Ratio",
}


def compute_fundamental_score(fundamentals: FundamentalsResult) -> FundamentalScoreResult:
    all_metrics = {
        m.key: m.value
        for m in (
            fundamentals.valuation + fundamentals.growth + fundamentals.profitability + fundamentals.balance_sheet
        )
    }

    factors: list[FundamentalScoreFactor] = []
    for key, points, is_healthy in _RULES:
        value = all_metrics.get(key)
        if value is None:
            factors.append(
                FundamentalScoreFactor(key=key, label=_LABELS[key], value=None, healthy=None, points=0.0, max_points=0.0)
            )
            continue
        healthy = bool(is_healthy(value))
        factors.append(
            FundamentalScoreFactor(
                key=key,
                label=_LABELS[key],
                value=value,
                healthy=healthy,
                points=points if healthy else 0.0,
                max_points=points,
            )
        )

    available = [f for f in factors if f.value is not None]
    if not available:
        return FundamentalScoreResult(score=None, factors=factors)

    total_points = sum(f.points for f in available)
    max_points = sum(f.max_points for f in available)
    score = round((total_points / max_points) * 100, 1) if max_points > 0 else None

    return FundamentalScoreResult(score=score, factors=factors)


def compute_overall_score(
    technical_score: float,
    fundamental_score: float | None,
    technical_weight: float,
    fundamental_weight: float,
) -> float | None:
    """Explicit weighted blend - never a silent average. If the fundamental
    score is unavailable, returns None rather than pretending the technical
    score alone represents a blended "overall" figure under a different name.
    """
    if fundamental_score is None:
        return None
    total_weight = technical_weight + fundamental_weight
    if total_weight <= 0:
        return None
    return round(
        (technical_score * technical_weight + fundamental_score * fundamental_weight) / total_weight, 1
    )
