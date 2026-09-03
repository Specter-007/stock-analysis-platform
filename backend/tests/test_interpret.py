"""Tests for app.indicators.interpret - these guard against copy/paste bugs
where a shared message accidentally gets reused across per-band or
per-indicator entries that should each describe their OWN current value.
"""
import pandas as pd

from app.indicators import interpret


def _row(**overrides):
    base = {
        "Close": 100.0,
        "SMA_20": 95.0, "SMA_50": 90.0, "SMA_100": 85.0, "SMA_200": 80.0,
        "EMA_20": 96.0, "EMA_50": 91.0,
        "RSI_14": 55.0,
        "MACD": 1.0, "MACD_SIGNAL": 0.5, "MACD_HIST": 0.5,
        "ROC_12": 2.0,
        "ATR_14": 2.0,
        "BB_UPPER": 105.0, "BB_MIDDLE": 100.0, "BB_LOWER": 95.0,
        "HIST_VOL_20": 20.0,
        "Volume": 1_000_000.0, "VOLUME_SMA_20": 900_000.0, "REL_VOLUME": 1.1,
        "DIST_SMA_20_PCT": 5.0, "DIST_SMA_50_PCT": 10.0, "DIST_SMA_200_PCT": 20.0,
    }
    base.update(overrides)
    return pd.Series(base)


def test_bollinger_upper_and_lower_have_distinct_interpretations_when_price_is_neutral():
    row = _row(Close=100.0, BB_UPPER=105.0, BB_LOWER=95.0)
    indicators = {iv["key"]: iv for iv in interpret.build_volatility_indicators(row, "Normal")}
    assert indicators["bb_upper"]["interpretation"] != indicators["bb_lower"]["interpretation"]
    assert indicators["bb_upper"]["status"] == "neutral"
    assert indicators["bb_lower"]["status"] == "neutral"


def test_bollinger_upper_breach_does_not_mislabel_lower_band():
    # Price above the upper band: the upper band entry should warn, but the
    # lower band entry must NOT claim price is also at/below the lower band.
    row = _row(Close=110.0, BB_UPPER=105.0, BB_LOWER=95.0)
    indicators = {iv["key"]: iv for iv in interpret.build_volatility_indicators(row, "Normal")}
    assert "overbought" in indicators["bb_upper"]["interpretation"]
    assert "oversold" not in indicators["bb_lower"]["interpretation"]
    assert indicators["bb_lower"]["status"] == "neutral"


def test_bollinger_lower_breach_does_not_mislabel_upper_band():
    row = _row(Close=90.0, BB_UPPER=105.0, BB_LOWER=95.0)
    indicators = {iv["key"]: iv for iv in interpret.build_volatility_indicators(row, "Normal")}
    assert "oversold" in indicators["bb_lower"]["interpretation"]
    assert "overbought" not in indicators["bb_upper"]["interpretation"]
    assert indicators["bb_upper"]["status"] == "neutral"


def test_trend_indicators_reference_correct_sma_value_each():
    row = _row(Close=100.0, SMA_20=95.0, SMA_50=90.0, SMA_100=85.0, SMA_200=80.0)
    indicators = {iv["key"]: iv for iv in interpret.build_trend_indicators(row)}
    assert indicators["sma_20"]["value"] == 95.0
    assert indicators["sma_50"]["value"] == 90.0
    assert indicators["sma_100"]["value"] == 85.0
    assert indicators["sma_200"]["value"] == 80.0


def test_unavailable_when_missing_data():
    row = _row(BB_UPPER=None, BB_MIDDLE=None, BB_LOWER=None)
    indicators = {iv["key"]: iv for iv in interpret.build_volatility_indicators(row, "Normal")}
    assert indicators["bb_upper"]["status"] == "unavailable"
    assert indicators["bb_lower"]["status"] == "unavailable"
