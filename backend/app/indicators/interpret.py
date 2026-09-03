"""Turns raw indicator values (for one specific stock, one specific day)
into human-readable interpretation + status labels for the UI. Every string
here is built from the actual computed value - nothing generic or canned.
"""
from __future__ import annotations

import pandas as pd

from app.indicators.compute import safe_float


def _iv(key: str, label: str, value: float | None, unit: str, interpretation: str, status: str) -> dict:
    return {
        "key": key,
        "label": label,
        "value": value,
        "unit": unit,
        "interpretation": interpretation,
        "status": status,
    }


def _unavailable(key: str, label: str, unit: str = "") -> dict:
    return _iv(key, label, None, unit, "Not enough historical data to calculate this indicator yet.", "unavailable")


def _sma_or_ema(key: str, label: str, value: float | None, close: float | None) -> dict:
    if value is None or close is None:
        return _unavailable(key, label, "$")
    above = close > value
    return _iv(
        key,
        label,
        round(value, 2),
        "$",
        f"Price is {'above' if above else 'below'} {label} — {'bullish' if above else 'bearish'} trend signal.",
        "bullish" if above else "bearish",
    )


def build_trend_indicators(row: pd.Series) -> list[dict]:
    close = safe_float(row.get("Close"))
    out = []
    for w in (20, 50, 100, 200):
        out.append(_sma_or_ema(f"sma_{w}", f"SMA {w}", safe_float(row.get(f"SMA_{w}")), close))
    for w in (20, 50):
        out.append(_sma_or_ema(f"ema_{w}", f"EMA {w}", safe_float(row.get(f"EMA_{w}")), close))
    return out


def build_momentum_indicators(row: pd.Series) -> list[dict]:
    out = []

    rsi = safe_float(row.get("RSI_14"))
    if rsi is None:
        out.append(_unavailable("rsi_14", "RSI (14)"))
    else:
        if rsi > 70:
            interp, status = "Overbought — elevated pullback risk.", "warning"
        elif rsi >= 50:
            interp, status = "Bullish momentum, not overbought.", "bullish"
        elif rsi >= 45:
            interp, status = "Neutral momentum.", "neutral"
        elif rsi >= 30:
            interp, status = "Weakening / bearish momentum.", "bearish"
        else:
            interp, status = "Oversold — potential bearish extreme.", "warning"
        out.append(_iv("rsi_14", "RSI (14)", round(rsi, 1), "", interp, status))

    macd = safe_float(row.get("MACD"))
    signal = safe_float(row.get("MACD_SIGNAL"))
    hist = safe_float(row.get("MACD_HIST"))
    if macd is None or signal is None:
        out.append(_unavailable("macd", "MACD"))
        out.append(_unavailable("macd_signal", "MACD Signal"))
        out.append(_unavailable("macd_hist", "MACD Histogram"))
    else:
        bullish = macd > signal
        out.append(
            _iv(
                "macd",
                "MACD",
                round(macd, 2),
                "",
                f"MACD line is {'above' if bullish else 'below'} its signal line — {'bullish' if bullish else 'bearish'}.",
                "bullish" if bullish else "bearish",
            )
        )
        out.append(_iv("macd_signal", "MACD Signal", round(signal, 2), "", "9-period EMA of the MACD line.", "neutral"))
        if hist is not None:
            out.append(
                _iv(
                    "macd_hist",
                    "MACD Histogram",
                    round(hist, 2),
                    "",
                    f"Histogram is {'positive' if hist > 0 else 'negative'} ({'widening' if abs(hist) > 0 else 'flat'} momentum).",
                    "bullish" if hist > 0 else "bearish",
                )
            )
        else:
            out.append(_unavailable("macd_hist", "MACD Histogram"))

    roc = safe_float(row.get("ROC_12"))
    if roc is None:
        out.append(_unavailable("roc_12", "Rate of Change (12)", "%"))
    else:
        status = "bullish" if roc > 1 else ("bearish" if roc < -1 else "neutral")
        out.append(
            _iv(
                "roc_12",
                "Rate of Change (12)",
                round(roc, 2),
                "%",
                f"Price has moved {roc:+.2f}% over the last 12 periods.",
                status,
            )
        )

    return out


def build_volatility_indicators(row: pd.Series, regime: str) -> list[dict]:
    out = []
    close = safe_float(row.get("Close"))

    atr = safe_float(row.get("ATR_14"))
    if atr is None:
        out.append(_unavailable("atr_14", "ATR (14)", "$"))
    else:
        atr_pct = (atr / close * 100) if close else None
        detail = f"Average daily range of ${atr:.2f}"
        if atr_pct is not None:
            detail += f" ({atr_pct:.1f}% of price)."
        out.append(_iv("atr_14", "ATR (14)", round(atr, 2), "$", detail, "neutral"))

    upper = safe_float(row.get("BB_UPPER"))
    middle = safe_float(row.get("BB_MIDDLE"))
    lower = safe_float(row.get("BB_LOWER"))
    if None in (upper, middle, lower, close):
        out.append(_unavailable("bb_upper", "Bollinger Upper Band", "$"))
        out.append(_unavailable("bb_middle", "Bollinger Middle Band", "$"))
        out.append(_unavailable("bb_lower", "Bollinger Lower Band", "$"))
    else:
        breached_upper = close >= upper
        breached_lower = close <= lower

        upper_status = "warning" if breached_upper else "neutral"
        upper_note = (
            "Price is at/above the upper band — potentially overbought."
            if breached_upper
            else f"Price is ${upper - close:.2f} below the upper band."
        )
        out.append(_iv("bb_upper", "Bollinger Upper Band", round(upper, 2), "$", upper_note, upper_status))

        out.append(
            _iv("bb_middle", "Bollinger Middle Band (SMA 20)", round(middle, 2), "$", "20-day moving average.", "neutral")
        )

        lower_status = "warning" if breached_lower else "neutral"
        lower_note = (
            "Price is at/below the lower band — potentially oversold."
            if breached_lower
            else f"Price is ${close - lower:.2f} above the lower band."
        )
        out.append(_iv("bb_lower", "Bollinger Lower Band", round(lower, 2), "$", lower_note, lower_status))

    hv = safe_float(row.get("HIST_VOL_20"))
    if hv is None:
        out.append(_unavailable("hist_vol_20", "Historical Volatility (20d, annualized)", "%"))
    else:
        status_map = {"Low": "bullish", "Normal": "neutral", "Elevated": "warning", "Extreme": "warning"}
        out.append(
            _iv(
                "hist_vol_20",
                "Historical Volatility (20d, annualized)",
                round(hv, 1),
                "%",
                f"Volatility regime is {regime} relative to this stock's own trailing history.",
                status_map.get(regime, "neutral"),
            )
        )

    return out


def build_volume_indicators(row: pd.Series) -> list[dict]:
    out = []
    volume = safe_float(row.get("Volume"))
    vol_sma = safe_float(row.get("VOLUME_SMA_20"))
    rel_vol = safe_float(row.get("REL_VOLUME"))

    out.append(_iv("volume", "Volume", volume, "shares", "Shares traded in the latest session.", "neutral") if volume is not None else _unavailable("volume", "Volume", "shares"))
    out.append(
        _iv("volume_sma_20", "Volume SMA (20)", round(vol_sma, 0), "shares", "20-day average trading volume.", "neutral")
        if vol_sma is not None
        else _unavailable("volume_sma_20", "Volume SMA (20)", "shares")
    )
    if rel_vol is None:
        out.append(_unavailable("relative_volume", "Relative Volume"))
    else:
        status = "bullish" if rel_vol > 1.2 else ("warning" if rel_vol < 0.5 else "neutral")
        out.append(
            _iv(
                "relative_volume",
                "Relative Volume",
                round(rel_vol, 2),
                "x",
                f"Trading at {rel_vol:.2f}x the 20-day average volume.",
                status,
            )
        )
    return out


def build_price_relationship_indicators(row: pd.Series) -> list[dict]:
    out = []
    for w in (20, 50, 200):
        dist = safe_float(row.get(f"DIST_SMA_{w}_PCT"))
        key = f"dist_sma_{w}_pct"
        label = f"Distance from SMA {w}"
        if dist is None:
            out.append(_unavailable(key, label, "%"))
        else:
            status = "bullish" if dist > 0 else ("bearish" if dist < 0 else "neutral")
            out.append(
                _iv(
                    key,
                    label,
                    round(dist, 2),
                    "%",
                    f"Price is {abs(dist):.2f}% {'above' if dist > 0 else 'below'} its {w}-day SMA.",
                    status,
                )
            )
    return out
