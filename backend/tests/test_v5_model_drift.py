"""V5: model drift monitoring - signal distribution, factor distribution,
and regime distribution comparisons between a historical baseline and a
recent window. Heavy sub-computations (signal history, regime
classification) are exercised through the real engine on synthetic price
data for the end-to-end case, and mocked for deterministic unit coverage
of the threshold/labeling logic itself.
"""
import numpy as np
import pandas as pd
import pytest

from app.model_evaluation import drift as drift_module
from app.signals.engine import ScoreFactor, SignalResult


def _make_ohlcv(n, seed, drift=0.0, vol=0.01, start_price=100.0):
    rng = np.random.default_rng(seed)
    log_returns = rng.normal(loc=drift, scale=vol, size=n)
    close = start_price * np.exp(np.cumsum(log_returns))
    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1]
    noise = rng.uniform(0.001, 0.01, size=n)
    high = np.maximum(open_, close) * (1 + noise)
    low = np.minimum(open_, close) * (1 - noise)
    volume = rng.integers(1_000_000, 10_000_000, size=n).astype(float)
    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=index)


def _fake_signal_result(signal: str, category_points: dict) -> SignalResult:
    factors = [
        ScoreFactor(category=cat, name=f"{cat}_factor", points=pts, min_points=-15, max_points=15,
                    detail="", polarity="positive" if pts > 0 else ("negative" if pts < 0 else "neutral"))
        for cat, pts in category_points.items()
    ]
    return SignalResult(signal=signal, score=50.0, raw_score=0.0, raw_min=-100, raw_max=100, factors=factors)


@pytest.fixture
def long_ohlcv():
    return _make_ohlcv(500, seed=1, drift=0.0003, vol=0.012)


def test_insufficient_data_flagged_for_short_history(monkeypatch, long_ohlcv):
    short_history = [(f"2024-01-{i:02d}", _fake_signal_result("HOLD", {"Trend": 5})) for i in range(1, 10)]
    monkeypatch.setattr(drift_module.history_module, "compute_signal_history_full", lambda *a, **kw: short_history)

    result = drift_module.detect_model_drift(
        ticker="TEST", full_price_df=long_ohlcv, benchmark="SPY", benchmark_full_price_df=long_ohlcv,
    )
    assert result.insufficient_data is True
    assert result.signal_distribution is None


def test_signal_drift_flagged_when_bucket_shifts_beyond_threshold(monkeypatch, long_ohlcv):
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=200)
    historical = [(str(d.date()), _fake_signal_result("BUY", {"Trend": 5})) for d in dates[:150]]
    recent = [(str(d.date()), _fake_signal_result("SELL", {"Trend": -5})) for d in dates[150:]]
    fake_history = historical + recent
    monkeypatch.setattr(drift_module.history_module, "compute_signal_history_full", lambda *a, **kw: fake_history)
    monkeypatch.setattr(drift_module, "classify_market_regime", lambda *a, **kw: type("R", (), {"regime": "BULL"})())

    result = drift_module.detect_model_drift(
        ticker="TEST", full_price_df=long_ohlcv, benchmark="SPY", benchmark_full_price_df=long_ohlcv,
        recent_window=50,
    )
    assert result.insufficient_data is False
    assert result.signal_distribution.flagged is True
    assert "BUY" in result.signal_distribution.shifted_buckets
    assert "SELL" in result.signal_distribution.shifted_buckets
    assert result.signal_distribution.historical_percent["BUY"] == 100.0
    assert result.signal_distribution.recent_percent["SELL"] == 100.0


def test_no_drift_flagged_when_distribution_is_stable(monkeypatch, long_ohlcv):
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=200)
    fake_history = [(str(d.date()), _fake_signal_result("HOLD", {"Trend": 1})) for d in dates]
    monkeypatch.setattr(drift_module.history_module, "compute_signal_history_full", lambda *a, **kw: fake_history)
    monkeypatch.setattr(drift_module, "classify_market_regime", lambda *a, **kw: type("R", (), {"regime": "SIDEWAYS"})())

    result = drift_module.detect_model_drift(
        ticker="TEST", full_price_df=long_ohlcv, benchmark="SPY", benchmark_full_price_df=long_ohlcv,
        recent_window=50,
    )
    assert result.signal_distribution.flagged is False
    assert result.regime_distribution.flagged is False


def test_factor_drift_flagged_when_category_mix_shifts(monkeypatch, long_ohlcv):
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=200)
    historical = [(str(d.date()), _fake_signal_result("BUY", {"Trend": 10, "Momentum": 2})) for d in dates[:150]]
    recent = [(str(d.date()), _fake_signal_result("BUY", {"Trend": 1, "Momentum": 10})) for d in dates[150:]]
    fake_history = historical + recent
    monkeypatch.setattr(drift_module.history_module, "compute_signal_history_full", lambda *a, **kw: fake_history)
    monkeypatch.setattr(drift_module, "classify_market_regime", lambda *a, **kw: type("R", (), {"regime": "BULL"})())

    result = drift_module.detect_model_drift(
        ticker="TEST", full_price_df=long_ohlcv, benchmark="SPY", benchmark_full_price_df=long_ohlcv,
        recent_window=50,
    )
    assert result.factor_distribution.flagged is True
    assert "Trend" in result.factor_distribution.shifted_buckets


def test_regime_drift_flagged_when_regime_mix_shifts(monkeypatch, long_ohlcv):
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=200)
    fake_history = [(str(d.date()), _fake_signal_result("HOLD", {"Trend": 1})) for d in dates]
    monkeypatch.setattr(drift_module.history_module, "compute_signal_history_full", lambda *a, **kw: fake_history)

    call_count = {"n": 0}

    def fake_classify(benchmark, sliced):
        call_count["n"] += 1
        # First 150 calls (historical window) look BULL, last 50 (recent) look BEAR.
        regime = "BULL" if call_count["n"] <= 150 else "BEAR"
        return type("R", (), {"regime": regime})()

    monkeypatch.setattr(drift_module, "classify_market_regime", fake_classify)

    result = drift_module.detect_model_drift(
        ticker="TEST", full_price_df=long_ohlcv, benchmark="SPY", benchmark_full_price_df=long_ohlcv,
        recent_window=50,
    )
    assert result.regime_distribution.flagged is True
    assert result.regime_distribution.historical_percent.get("BULL") == 100.0
    assert result.regime_distribution.recent_percent.get("BEAR") == 100.0


def test_end_to_end_with_real_signal_engine_does_not_crash(long_ohlcv):
    """Full integration through the real signal engine and regime
    classifier - no mocks. Only asserts it runs and returns a coherent
    shape; the specific drift verdict depends on the real (random)
    synthetic price path and isn't asserted here.
    """
    result = drift_module.detect_model_drift(
        ticker="TEST", full_price_df=long_ohlcv, benchmark="SPY", benchmark_full_price_df=long_ohlcv,
        lookback_sessions=300, recent_window=60,
    )
    assert result.insufficient_data is False
    assert sum(result.signal_distribution.historical_percent.values()) == pytest.approx(100.0, abs=0.5)
    assert sum(result.signal_distribution.recent_percent.values()) == pytest.approx(100.0, abs=0.5)
    assert sum(result.factor_distribution.historical_percent.values()) == pytest.approx(100.0, abs=0.5)


def test_methodology_discloses_threshold_not_hypothesis_test(long_ohlcv):
    result = drift_module.detect_model_drift(
        ticker="TEST", full_price_df=long_ohlcv, benchmark="SPY", benchmark_full_price_df=long_ohlcv,
    )
    assert "not a formal hypothesis test" in result.methodology
