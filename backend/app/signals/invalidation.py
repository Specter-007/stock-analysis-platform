"""'What could invalidate this signal?' - derived directly from the factors
that are CURRENTLY supporting the signal's direction, using their actual
current values. Never generic boilerplate unrelated to the ticker's state.
"""
from __future__ import annotations

from app.signals.engine import ScoreFactor, SignalResult

_BULLISH_FLIP_TEMPLATES = {
    "Price vs. 200-day SMA": "Price falling back below the 200-day SMA.",
    "50-day SMA vs. 200-day SMA": "A 'death cross' - the 50-day SMA falling back below the 200-day SMA.",
    "20-day SMA vs. 50-day SMA": "The 20-day SMA crossing back below the 50-day SMA.",
    "RSI (14)": "Momentum fading, with RSI dropping back below 50.",
    "MACD": "MACD crossing back below its signal line (bearish crossover).",
    "Rate of Change (12)": "12-period momentum turning negative.",
    "Volume confirmation": "A reversal move occurring on above-average volume.",
    "Volatility regime": "Volatility becoming Elevated or Extreme, reducing model confidence.",
}

_BEARISH_FLIP_TEMPLATES = {
    "Price vs. 200-day SMA": "Price reclaiming the 200-day SMA.",
    "50-day SMA vs. 200-day SMA": "A 'golden cross' - the 50-day SMA crossing back above the 200-day SMA.",
    "20-day SMA vs. 50-day SMA": "The 20-day SMA crossing back above the 50-day SMA.",
    "RSI (14)": "A bullish momentum recovery, with RSI climbing back above 50.",
    "MACD": "MACD crossing back above its signal line (bullish crossover).",
    "Rate of Change (12)": "12-period momentum turning positive.",
    "Volume confirmation": "A recovery move occurring on above-average volume.",
    "Volatility regime": "Volatility normalizing from an Elevated/Extreme regime.",
}


def _factor_flip_note(factor: ScoreFactor, templates: dict[str, str]) -> str:
    template = templates.get(factor.name, f"{factor.name} reversing from its current reading.")
    return f"{factor.name}: {template} (currently: {factor.detail})"


def what_could_invalidate(result: SignalResult) -> list[str]:
    """For a BUY-class signal: what would need to happen among the factors
    CURRENTLY supporting it to flip it toward SELL/HOLD.
    For a SELL-class signal: the mirror image.
    For HOLD: there's no strong directional bias to invalidate.
    """
    if result.signal in ("BUY", "STRONG_BUY"):
        supporting = [f for f in result.factors if f.polarity == "positive"]
        return [_factor_flip_note(f, _BULLISH_FLIP_TEMPLATES) for f in supporting]

    if result.signal in ("SELL", "STRONG_SELL"):
        supporting = [f for f in result.factors if f.polarity == "negative"]
        return [_factor_flip_note(f, _BEARISH_FLIP_TEMPLATES) for f in supporting]

    return [
        "Signal is HOLD - there is no strong directional bias for a move in either "
        "direction to invalidate. A clear break above the resistance implied by the "
        "positive factors, or below the support implied by the negative factors, would "
        "be needed to establish a new BUY or SELL signal."
    ]
