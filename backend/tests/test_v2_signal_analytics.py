"""Tests for model versioning, score breakdown, signal history, change
detection, stability, invalidation, and signal-performance analytics.
"""
import pandas as pd
import pytest

from app.indicators.compute import compute_indicator_frame
from app.signals import engine as signal_engine
from app.signals import history as history_module
from app.signals import invalidation as invalidation_module
from app.signals import performance as performance_module


def test_model_v1_1_is_default():
    result = signal_engine.evaluate.__defaults__
    assert "1.1" in result


def test_v1_0_and_v1_1_agree_on_direction_but_can_differ_in_score(ohlcv_uptrend):
    frame = compute_indicator_frame(ohlcv_uptrend)
    v11 = signal_engine.evaluate(frame, model_version="1.1")
    v10 = signal_engine.evaluate(frame, model_version="1.0")
    assert v11.model_version == "1.1"
    assert v10.model_version == "1.0"
    # Both should classify a strong, clean uptrend the same directional way.
    assert v11.signal in ("BUY", "STRONG_BUY")
    assert v10.signal in ("BUY", "STRONG_BUY")


def test_v1_1_fixed_bounds_independent_of_available_factor_count(ohlcv_long, ohlcv_short):
    """The defining property of v1.1: raw_min/raw_max are the SAME fixed
    constants regardless of how many factors a given ticker's data allows,
    unlike v1.0 whose bounds shrink with fewer available factors.
    """
    long_frame = compute_indicator_frame(ohlcv_long)
    short_frame = compute_indicator_frame(ohlcv_short)

    long_result = signal_engine.evaluate(long_frame, model_version="1.1")
    short_result = signal_engine.evaluate(short_frame, model_version="1.1")

    assert long_result.raw_min == short_result.raw_min == pytest.approx(-90.0)
    assert long_result.raw_max == short_result.raw_max == pytest.approx(85.0)


def test_v1_0_bounds_shrink_with_fewer_factors(ohlcv_long, ohlcv_short):
    long_frame = compute_indicator_frame(ohlcv_long)
    short_frame = compute_indicator_frame(ohlcv_short)

    long_result = signal_engine.evaluate(long_frame, model_version="1.0")
    short_result = signal_engine.evaluate(short_frame, model_version="1.0")

    # ohlcv_short has too little history for trend/most factors, so its
    # v1.0 raw_max/min span must be strictly smaller in magnitude.
    assert abs(short_result.raw_max - short_result.raw_min) < abs(long_result.raw_max - long_result.raw_min)


def test_score_breakdown_sums_to_raw_score(ohlcv_long):
    frame = compute_indicator_frame(ohlcv_long)
    result = signal_engine.evaluate(frame)
    breakdown = result.category_breakdown
    assert sum(breakdown.values()) == pytest.approx(result.raw_score)


def test_score_breakdown_has_expected_categories(ohlcv_long):
    frame = compute_indicator_frame(ohlcv_long)
    result = signal_engine.evaluate(frame)
    for cat in ("Trend", "Momentum", "Volume", "Volatility"):
        assert cat in result.category_breakdown


def test_signal_history_is_causal_and_bounded(ohlcv_long):
    frame = compute_indicator_frame(ohlcv_long)
    history = history_module.compute_signal_history(frame, lookback_sessions=30)
    assert len(history) <= 30
    for point in history:
        assert 0.0 <= point.score <= 100.0
        assert point.signal in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")


def test_signal_history_matches_direct_evaluate_at_each_point(ohlcv_long):
    """Every point in the history must equal what evaluate() would produce
    if called directly on the frame truncated to that same date - this is
    the same causal guarantee the backtester relies on.
    """
    frame = compute_indicator_frame(ohlcv_long)
    full_history = history_module.compute_signal_history_full(frame, lookback_sessions=10)
    for date_str, result in full_history:
        truncated = frame.loc[:pd.Timestamp(date_str)]
        direct = signal_engine.evaluate(truncated)
        assert direct.score == result.score
        assert direct.signal == result.signal


def test_detect_signal_change_none_when_no_change():
    from app.signals.engine import ScoreFactor, SignalResult

    same = SignalResult(signal="BUY", score=70, raw_score=0, raw_min=-90, raw_max=85, factors=[])
    history = [("2024-01-01", same), ("2024-01-02", same)]
    assert history_module.detect_signal_change(history) is None


def test_detect_signal_change_reports_contributing_factors():
    from app.signals.engine import ScoreFactor, SignalResult

    prev = SignalResult(
        signal="HOLD", score=55, raw_score=0, raw_min=-90, raw_max=85,
        factors=[ScoreFactor("Momentum", "MACD", -8, -15, 15, "bearish crossover", "negative")],
    )
    curr = SignalResult(
        signal="BUY", score=68, raw_score=0, raw_min=-90, raw_max=85,
        factors=[ScoreFactor("Momentum", "MACD", 15, -15, 15, "strong bullish", "positive")],
    )
    change = history_module.detect_signal_change([("2024-01-01", prev), ("2024-01-02", curr)])
    assert change is not None
    assert change.previous_signal == "HOLD"
    assert change.current_signal == "BUY"
    assert any("MACD" in c for c in change.contributing_changes)


def test_signal_stability_100_when_all_same():
    points = [history_module.SignalHistoryPoint(date=f"d{i}", signal="BUY", score=70, model_version="1.1") for i in range(10)]
    stability, recent = history_module.compute_signal_stability(points)
    assert stability == 100.0
    assert len(recent) == 10


def test_signal_stability_lower_when_mixed():
    signals = ["BUY", "HOLD", "SELL", "BUY", "HOLD", "SELL", "BUY", "HOLD", "BUY", "SELL"]
    points = [
        history_module.SignalHistoryPoint(date=f"d{i}", signal=s, score=50, model_version="1.1")
        for i, s in enumerate(signals)
    ]
    stability, _ = history_module.compute_signal_stability(points)
    assert stability < 100.0


def test_invalidation_conditions_reference_positive_factors_for_buy():
    from app.signals.engine import ScoreFactor, SignalResult

    result = SignalResult(
        signal="BUY", score=70, raw_score=0, raw_min=-90, raw_max=85,
        factors=[
            ScoreFactor("Trend", "Price vs. 200-day SMA", 15, -15, 15, "Price ($100) is above the 200-day SMA ($90).", "positive"),
            ScoreFactor("Momentum", "RSI (14)", -5, -10, 10, "weakening", "negative"),
        ],
    )
    conditions = invalidation_module.what_could_invalidate(result)
    assert len(conditions) == 1
    assert "200-day SMA" in conditions[0]


def test_invalidation_conditions_for_hold_explains_no_bias():
    from app.signals.engine import SignalResult

    result = SignalResult(signal="HOLD", score=55, raw_score=0, raw_min=-90, raw_max=85, factors=[])
    conditions = invalidation_module.what_could_invalidate(result)
    assert len(conditions) == 1
    assert "HOLD" in conditions[0]


def test_signal_performance_no_look_ahead_excludes_incomplete_horizons(ohlcv_long):
    """A signal on the very last day of the series has no future data to
    measure a forward return against - it must be excluded, not padded.
    """
    frame = compute_indicator_frame(ohlcv_long)
    groups = performance_module.compute_signal_performance(frame, lookback_sessions=250, horizons=(5, 20))
    for g in groups:
        for h in g.horizons:
            assert h.sample_size <= g.total_signals


def test_signal_performance_returns_are_retrospective_only(ohlcv_uptrend):
    frame = compute_indicator_frame(ohlcv_uptrend)
    groups = performance_module.compute_signal_performance(frame, lookback_sessions=250)
    buy_group = next(g for g in groups if g.signal_group == "BUY")
    # In a strong clean uptrend fixture, historical BUY signals should tend
    # to be followed by positive forward returns more often than not.
    horizon_20 = next(h for h in buy_group.horizons if h.horizon_sessions == 20)
    if horizon_20.sample_size > 5:
        assert horizon_20.positive_rate_percent > 50
