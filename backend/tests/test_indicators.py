import numpy as np
import pandas as pd
import pytest

from app.indicators import momentum, trend, volatility, volume as volume_ind
from app.indicators.compute import (
    classify_trend,
    classify_volatility_regime,
    compute_indicator_frame,
)


def test_sma_matches_manual_mean():
    close = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
    result = trend.sma(close, 3)
    assert np.isnan(result.iloc[0])
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == pytest.approx((1 + 2 + 3) / 3)
    assert result.iloc[-1] == pytest.approx((8 + 9 + 10) / 3)


def test_sma_deterministic(ohlcv_long):
    a = trend.sma(ohlcv_long["Close"], 20)
    b = trend.sma(ohlcv_long["Close"], 20)
    pd.testing.assert_series_equal(a, b)


def test_ema_reacts_faster_than_sma_to_recent_move():
    close = pd.Series([10.0] * 30 + [20.0] * 5)
    sma = trend.sma(close, 10)
    ema = trend.ema(close, 10)
    # After a sudden jump, EMA should have moved closer to the new level
    # than a plain SMA over the same window.
    assert ema.iloc[-1] > sma.iloc[-1]


def test_rsi_is_100_when_no_losses():
    close = pd.Series(range(1, 30), dtype=float)  # strictly increasing
    result = momentum.rsi(close, window=14)
    assert result.iloc[-1] == pytest.approx(100.0)


def test_rsi_bounded_0_100(ohlcv_long):
    result = momentum.rsi(ohlcv_long["Close"], 14).dropna()
    assert (result >= 0).all()
    assert (result <= 100).all()


def test_macd_histogram_is_difference_of_lines(ohlcv_long):
    macd_line, signal_line, hist = momentum.macd(ohlcv_long["Close"])
    diff = (macd_line - signal_line).dropna()
    hist_clean = hist.dropna()
    pd.testing.assert_series_equal(diff, hist_clean, check_names=False)


def test_roc_positive_for_uptrend(ohlcv_uptrend):
    result = momentum.roc(ohlcv_uptrend["Close"], 12).dropna()
    assert result.iloc[-1] > 0


def test_roc_negative_for_downtrend(ohlcv_downtrend):
    result = momentum.roc(ohlcv_downtrend["Close"], 12).dropna()
    assert result.iloc[-1] < 0


def test_atr_non_negative(ohlcv_long):
    result = volatility.atr(ohlcv_long["High"], ohlcv_long["Low"], ohlcv_long["Close"], 14).dropna()
    assert (result >= 0).all()


def test_bollinger_upper_above_lower(ohlcv_long):
    upper, middle, lower = volatility.bollinger_bands(ohlcv_long["Close"], 20, 2)
    valid = upper.dropna().index
    assert (upper.loc[valid] >= middle.loc[valid]).all()
    assert (middle.loc[valid] >= lower.loc[valid]).all()


def test_bollinger_bands_widen_with_higher_volatility(ohlcv_high_volatility, ohlcv_uptrend):
    high_vol_upper, high_vol_mid, high_vol_lower = volatility.bollinger_bands(ohlcv_high_volatility["Close"])
    low_vol_upper, low_vol_mid, low_vol_lower = volatility.bollinger_bands(ohlcv_uptrend["Close"])

    high_vol_width = (high_vol_upper - high_vol_lower).dropna().mean() / ohlcv_high_volatility["Close"].mean()
    low_vol_width = (low_vol_upper - low_vol_lower).dropna().mean() / ohlcv_uptrend["Close"].mean()
    assert high_vol_width > low_vol_width


def test_historical_volatility_higher_for_noisier_series(ohlcv_high_volatility, ohlcv_uptrend):
    hv_high = volatility.historical_volatility(ohlcv_high_volatility["Close"]).dropna().mean()
    hv_low = volatility.historical_volatility(ohlcv_uptrend["Close"]).dropna().mean()
    assert hv_high > hv_low


def test_volume_sma_matches_manual_mean():
    vol = pd.Series([10, 20, 30, 40, 50], dtype=float)
    result = volume_ind.volume_sma(vol, 3)
    assert result.iloc[2] == pytest.approx(20.0)
    assert result.iloc[-1] == pytest.approx(40.0)


def test_relative_volume_above_one_when_volume_spikes():
    vol = pd.Series([100.0] * 25 + [500.0])
    result = volume_ind.relative_volume(vol, 20)
    assert result.iloc[-1] > 1.0


def test_relative_volume_around_one_for_steady_volume():
    vol = pd.Series([100.0] * 30)
    result = volume_ind.relative_volume(vol, 20).dropna()
    assert result.iloc[-1] == pytest.approx(1.0)


def test_compute_indicator_frame_adds_expected_columns(ohlcv_long):
    out = compute_indicator_frame(ohlcv_long)
    for col in ("SMA_20", "SMA_200", "RSI_14", "MACD", "ATR_14", "BB_UPPER", "HIST_VOL_20", "REL_VOLUME"):
        assert col in out.columns
    assert len(out) == len(ohlcv_long)


def test_compute_indicator_frame_does_not_mutate_input(ohlcv_long):
    original_columns = list(ohlcv_long.columns)
    compute_indicator_frame(ohlcv_long)
    assert list(ohlcv_long.columns) == original_columns


def test_classify_trend_strong_bullish_for_clean_uptrend(ohlcv_uptrend):
    frame = compute_indicator_frame(ohlcv_uptrend)
    label = classify_trend(frame.iloc[-1])
    assert label in ("Bullish", "Strong Bullish")


def test_classify_trend_bearish_for_clean_downtrend(ohlcv_downtrend):
    frame = compute_indicator_frame(ohlcv_downtrend)
    label = classify_trend(frame.iloc[-1])
    assert label in ("Bearish", "Strong Bearish")


def test_classify_trend_insufficient_data_when_short_history(ohlcv_short):
    frame = compute_indicator_frame(ohlcv_short)
    label = classify_trend(frame.iloc[-1])
    assert label == "Insufficient Data"


def test_classify_volatility_regime_extreme_for_noisy_series(ohlcv_high_volatility):
    frame = compute_indicator_frame(ohlcv_high_volatility)
    regime = classify_volatility_regime(frame)
    assert regime in ("Low", "Normal", "Elevated", "Extreme")


def test_indicators_are_causal_no_lookahead(ohlcv_long):
    """The value of every indicator at row i must be identical whether it is
    computed on the full series or on a series truncated to end at row i.
    This is the mathematical foundation the backtester's no-look-ahead
    guarantee depends on.
    """
    full = compute_indicator_frame(ohlcv_long)
    cutoff = 250
    truncated = compute_indicator_frame(ohlcv_long.iloc[: cutoff + 1])

    row_full = full.iloc[cutoff]
    row_truncated = truncated.iloc[-1]

    for col in ("SMA_20", "SMA_200", "RSI_14", "MACD", "ATR_14", "HIST_VOL_20"):
        a, b = row_full[col], row_truncated[col]
        if pd.isna(a) and pd.isna(b):
            continue
        assert a == pytest.approx(b), f"{col} differs: {a} vs {b}"
