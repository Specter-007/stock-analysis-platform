"""Model-based, present-tense risk context - NOT a prediction of future risk.

Every factor listed here is derived from the ticker's own actual retrieved
indicator values. Nothing is invented or generic; if a factor didn't
trigger for this specific stock right now, it isn't shown.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.indicators.compute import safe_float
from app.signals.engine import SignalResult
from app.utils.finance import max_drawdown

RISK_LEVELS = ("LOW", "MODERATE", "HIGH", "SEVERE")


@dataclass
class RiskResult:
    risk_level: str
    risk_score: int
    risk_factors: list[str] = field(default_factory=list)
    max_drawdown_pct: float | None = None
    atr_pct_of_price: float | None = None


def assess_risk(indicator_df: pd.DataFrame, result: SignalResult) -> RiskResult:
    row = indicator_df.iloc[-1]
    factors: list[str] = []
    score = 0

    close = safe_float(row.get("Close"))
    rsi = safe_float(row.get("RSI_14"))
    atr = safe_float(row.get("ATR_14"))
    dist_sma200 = safe_float(row.get("DIST_SMA_200_PCT"))

    regime = result.volatility_regime
    if regime == "Extreme":
        score += 3
        factors.append("Volatility is extreme relative to this stock's own trailing history.")
    elif regime == "Elevated":
        score += 2
        factors.append("Volatility is elevated relative to this stock's own trailing history.")
    elif regime == "Normal":
        score += 1

    if rsi is not None:
        if rsi > 70:
            score += 1
            factors.append(f"RSI ({rsi:.1f}) is in overbought territory — pullback risk.")
        elif rsi < 30:
            score += 1
            factors.append(f"RSI ({rsi:.1f}) is in oversold territory — continued downside risk.")

    if dist_sma200 is not None and abs(dist_sma200) > 30:
        score += 1
        direction = "above" if dist_sma200 > 0 else "below"
        factors.append(
            f"Price is {abs(dist_sma200):.1f}% {direction} its 200-day SMA — extended from long-term trend."
        )

    atr_pct = None
    if atr is not None and close:
        atr_pct = (atr / close) * 100
        if atr_pct > 4.0:
            score += 1
            factors.append(f"Average True Range is {atr_pct:.1f}% of price — wide daily price swings.")

    negative_factors = result.negative_factors
    positive_factors = result.positive_factors
    if len(negative_factors) >= 3 and len(positive_factors) >= 1:
        score += 1
        factors.append("Multiple technical factors conflict, reducing signal reliability.")

    dd = max_drawdown(indicator_df["Close"])
    dd_pct = dd * 100 if dd is not None else None
    if dd_pct is not None and dd_pct < -40:
        score += 1
        factors.append(f"Historical maximum drawdown of {dd_pct:.1f}% indicates high downside potential.")

    if score >= 6:
        level = "SEVERE"
    elif score >= 4:
        level = "HIGH"
    elif score >= 2:
        level = "MODERATE"
    else:
        level = "LOW"

    if not factors:
        factors.append("No elevated risk factors detected in current indicator readings.")

    return RiskResult(
        risk_level=level,
        risk_score=score,
        risk_factors=factors,
        max_drawdown_pct=round(dd_pct, 2) if dd_pct is not None else None,
        atr_pct_of_price=round(atr_pct, 2) if atr_pct is not None else None,
    )
