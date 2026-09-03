import pandas as pd
import pytest

from app.indicators.compute import compute_indicator_frame
from app.signals import confidence as confidence_module
from app.signals import engine as signal_engine
from app.signals import risk as risk_module


def test_score_to_signal_thresholds():
    assert signal_engine.score_to_signal(100) == "STRONG_BUY"
    assert signal_engine.score_to_signal(80) == "STRONG_BUY"
    assert signal_engine.score_to_signal(79.9) == "BUY"
    assert signal_engine.score_to_signal(65) == "BUY"
    assert signal_engine.score_to_signal(64.9) == "HOLD"
    assert signal_engine.score_to_signal(45) == "HOLD"
    assert signal_engine.score_to_signal(44.9) == "SELL"
    assert signal_engine.score_to_signal(30) == "SELL"
    assert signal_engine.score_to_signal(29.9) == "STRONG_SELL"
    assert signal_engine.score_to_signal(0) == "STRONG_SELL"


def test_evaluate_score_is_normalized_0_to_100(ohlcv_long):
    frame = compute_indicator_frame(ohlcv_long)
    result = signal_engine.evaluate(frame)
    assert 0.0 <= result.score <= 100.0


def test_evaluate_is_deterministic(ohlcv_long):
    frame = compute_indicator_frame(ohlcv_long)
    r1 = signal_engine.evaluate(frame)
    r2 = signal_engine.evaluate(frame)
    assert r1.score == r2.score
    assert r1.signal == r2.signal
    assert [f.points for f in r1.factors] == [f.points for f in r2.factors]


def test_uptrend_scores_higher_than_downtrend(ohlcv_uptrend, ohlcv_downtrend):
    up = signal_engine.evaluate(compute_indicator_frame(ohlcv_uptrend))
    down = signal_engine.evaluate(compute_indicator_frame(ohlcv_downtrend))
    assert up.score > down.score
    assert up.signal in ("BUY", "STRONG_BUY")
    assert down.signal in ("SELL", "STRONG_SELL")


def test_evaluate_raises_on_empty_frame():
    with pytest.raises(ValueError):
        signal_engine.evaluate(pd.DataFrame())


def test_evaluate_handles_missing_indicators_gracefully(ohlcv_short):
    frame = compute_indicator_frame(ohlcv_short)
    result = signal_engine.evaluate(frame)
    # With only 10 days of data, long-window trend factors can't be computed;
    # the engine should still return a valid, bounded result using whatever
    # factors it does have, rather than raising or fabricating values.
    assert 0.0 <= result.score <= 100.0
    assert len(result.factors) < 8


def test_explanation_factors_partition_correctly(ohlcv_long):
    result = signal_engine.evaluate(compute_indicator_frame(ohlcv_long))
    all_factors = set(id(f) for f in result.factors)
    partitioned = set(id(f) for f in result.positive_factors + result.negative_factors + result.neutral_factors)
    assert all_factors == partitioned
    for f in result.positive_factors:
        assert f.points > 0
    for f in result.negative_factors:
        assert f.points < 0
    for f in result.neutral_factors:
        assert f.points == 0


def test_confidence_is_not_simply_score_divided_by_100(ohlcv_long):
    frame = compute_indicator_frame(ohlcv_long)
    result = signal_engine.evaluate(frame)
    conf = confidence_module.compute_confidence(result)
    assert conf.confidence_percent != pytest.approx(result.score)


def test_confidence_bounded_between_5_and_97(ohlcv_uptrend, ohlcv_downtrend, ohlcv_high_volatility):
    for fixture in (ohlcv_uptrend, ohlcv_downtrend, ohlcv_high_volatility):
        frame = compute_indicator_frame(fixture)
        result = signal_engine.evaluate(frame)
        conf = confidence_module.compute_confidence(result)
        assert 5.0 <= conf.confidence_percent <= 97.0


def test_confidence_lower_for_conflicting_factors():
    """Construct a signal result by hand with fully agreeing vs. fully
    conflicting factors to prove agreement actually moves confidence.
    """
    from app.signals.engine import ScoreFactor, SignalResult

    agreeing = SignalResult(
        signal="BUY",
        score=70.0,
        raw_score=10,
        raw_min=-10,
        raw_max=10,
        factors=[
            ScoreFactor("Trend", "a", 10, -10, 10, "d", "positive"),
            ScoreFactor("Momentum", "b", 10, -10, 10, "d", "positive"),
        ],
        trend_classification="Bullish",
        volatility_regime="Normal",
    )
    conflicting = SignalResult(
        signal="BUY",
        score=70.0,
        raw_score=10,
        raw_min=-10,
        raw_max=10,
        factors=[
            ScoreFactor("Trend", "a", 10, -10, 10, "d", "positive"),
            ScoreFactor("Momentum", "b", -10, -10, 10, "d", "negative"),
        ],
        trend_classification="Bullish",
        volatility_regime="Normal",
    )

    conf_agree = confidence_module.compute_confidence(agreeing)
    conf_conflict = confidence_module.compute_confidence(conflicting)
    assert conf_agree.confidence_percent > conf_conflict.confidence_percent


def test_risk_assessment_flags_extreme_volatility(ohlcv_high_volatility):
    frame = compute_indicator_frame(ohlcv_high_volatility)
    result = signal_engine.evaluate(frame)
    risk = risk_module.assess_risk(frame, result)
    assert risk.risk_level in risk_module.RISK_LEVELS
    assert isinstance(risk.risk_factors, list)
    assert len(risk.risk_factors) >= 1


def test_risk_factors_are_never_generic_placeholder_text(ohlcv_uptrend):
    frame = compute_indicator_frame(ohlcv_uptrend)
    result = signal_engine.evaluate(frame)
    risk = risk_module.assess_risk(frame, result)
    for factor in risk.risk_factors:
        assert factor != ""
        assert "lorem" not in factor.lower()
