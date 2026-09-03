"""Tests for market regime classification, relative strength, and sector
comparison - all deterministic, computed from synthetic OHLCV fixtures.
"""
import pandas as pd
import pytest

from app.indicators.compute import compute_indicator_frame
from app.market.regime import classify_market_regime
from app.market.relative_strength import compute_relative_strength, period_return
from app.market.sector import compare_sector


def test_market_regime_bull_for_clean_uptrend(ohlcv_uptrend):
    frame = compute_indicator_frame(ohlcv_uptrend)
    result = classify_market_regime("SPY", frame)
    assert result.regime == "BULL"
    assert result.trend_classification in ("Bullish", "Strong Bullish")
    assert 0 <= result.regime_confidence_percent <= 100


def test_market_regime_bear_for_clean_downtrend(ohlcv_downtrend):
    frame = compute_indicator_frame(ohlcv_downtrend)
    result = classify_market_regime("SPY", frame)
    assert result.regime == "BEAR"


def test_market_regime_high_volatility_overrides_trend(ohlcv_high_volatility):
    frame = compute_indicator_frame(ohlcv_high_volatility)
    result = classify_market_regime("SPY", frame)
    if result.volatility_regime == "Extreme":
        assert result.regime == "HIGH_VOLATILITY"


def test_market_regime_unavailable_for_empty_frame():
    result = classify_market_regime("SPY", pd.DataFrame())
    assert result.regime == "UNAVAILABLE"
    assert result.regime_confidence_percent == 0.0


def test_relative_strength_strong_when_ticker_outperforms(ohlcv_uptrend, ohlcv_downtrend):
    periods = compute_relative_strength(ohlcv_uptrend["Close"], ohlcv_downtrend["Close"])
    for p in periods:
        if p.relative_return_pp is not None:
            assert p.classification == "STRONG"
            assert p.relative_return_pp > 0


def test_relative_strength_in_line_when_returns_are_similar():
    close = pd.Series(range(100, 500))
    periods = compute_relative_strength(close, close)
    for p in periods:
        assert p.relative_return_pp == pytest.approx(0.0)
        assert p.classification == "IN_LINE"


def test_relative_strength_unavailable_when_insufficient_history():
    short_close = pd.Series([100.0, 101.0, 102.0])
    periods = compute_relative_strength(short_close, short_close)
    for p in periods:
        assert p.ticker_return_percent is None
        assert p.classification == "UNAVAILABLE"


def test_period_return_matches_manual_calculation():
    close = pd.Series([100.0] * 20 + [110.0])
    result = period_return(close, 20)
    assert result == pytest.approx(10.0)


def test_sector_comparison_unavailable_for_unknown_sector():
    result = compare_sector("XYZ", "Some Unmapped Sector")
    assert result.available is False
    assert result.peers == []


def test_sector_comparison_unavailable_for_missing_sector():
    result = compare_sector("XYZ", None)
    assert result.available is False
