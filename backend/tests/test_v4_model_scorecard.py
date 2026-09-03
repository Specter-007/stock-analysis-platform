"""V4 P2.6: Model Scorecard - five independent dimensions, each labeled from
an already-tested engine's own output. Heavy sub-computations (out-of-
sample, sensitivity, walk-forward, regime-performance) are mocked so these
tests deterministically exercise the LABELING logic, which is what this
module actually adds - the underlying engines have their own test suites.
"""
import pytest

from app.model_evaluation import scorecard as sc


@pytest.fixture(autouse=True)
def isolated(monkeypatch, ohlcv_long):
    # Sensible default mocks so a test that doesn't care about one dimension
    # doesn't have to hand-roll a full fake for it.
    class FakePeriod:
        def __init__(self, label, total_return, sharpe, trades, error=None):
            self.label = label
            self.total_return_percent = total_return
            self.sharpe_ratio = sharpe
            self.number_of_trades = trades
            self.error = error

    class FakeOOSResult:
        periods = [
            FakePeriod("IN_SAMPLE", 20.0, 1.2, 10),
            FakePeriod("VALIDATION", 15.0, 1.0, 8),
            FakePeriod("OUT_OF_SAMPLE", 10.0, 0.9, 6),
        ]

    monkeypatch.setattr(sc, "run_out_of_sample_validation", lambda **kw: FakeOOSResult())

    class FakeSensitivityParam:
        def __init__(self, robustness):
            self.robustness = robustness

    class FakeSensitivityResult:
        parameters = [FakeSensitivityParam("HIGHER_ROBUSTNESS"), FakeSensitivityParam("HIGHER_ROBUSTNESS")]

    monkeypatch.setattr(sc, "run_sensitivity_analysis", lambda **kw: FakeSensitivityResult())

    class FakeWalkForwardResult:
        folds = [object(), object(), object(), object()]
        folds_with_positive_return = 3

    monkeypatch.setattr(sc, "run_walk_forward", lambda **kw: FakeWalkForwardResult())

    monkeypatch.setattr(sc, "run_backtest", lambda **kw: object())

    class FakeBucket:
        def __init__(self, regime, trading_days, ret):
            self.regime = regime
            self.trading_days = trading_days
            self.compounded_return_percent = ret

    class FakeRegimeResult:
        buckets = [FakeBucket("BULL", 100, 12.0), FakeBucket("BEAR", 50, -3.0)]

    monkeypatch.setattr(sc, "compute_regime_performance", lambda *a, **kw: FakeRegimeResult())

    return ohlcv_long


def test_scorecard_has_five_named_dimensions(isolated):
    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    names = {d.name for d in result.dimensions}
    assert names == {
        "OUT_OF_SAMPLE_STRENGTH", "ROBUSTNESS", "WALK_FORWARD_STABILITY",
        "REGIME_DEPENDENCY", "FORWARD_PAPER_DATA",
    }


def test_no_default_composite_score_field(isolated):
    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    assert not hasattr(result, "composite_score")
    assert "No single composite score is computed by default" in result.composite_note


def test_out_of_sample_strong_when_oos_holds_up_relative_to_in_sample(isolated):
    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    dim = next(d for d in result.dimensions if d.name == "OUT_OF_SAMPLE_STRENGTH")
    assert dim.label == "STRONG"


def test_out_of_sample_weak_when_oos_negative(monkeypatch, isolated):
    class FakePeriod:
        def __init__(self, label, total_return, sharpe, trades):
            self.label = label
            self.total_return_percent = total_return
            self.sharpe_ratio = sharpe
            self.number_of_trades = trades
            self.error = None

    class FakeOOSResult:
        periods = [FakePeriod("IN_SAMPLE", 20.0, 1.2, 10), FakePeriod("OUT_OF_SAMPLE", -8.0, -0.5, 6)]

    monkeypatch.setattr(sc, "run_out_of_sample_validation", lambda **kw: FakeOOSResult())

    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    dim = next(d for d in result.dimensions if d.name == "OUT_OF_SAMPLE_STRENGTH")
    assert dim.label == "WEAK"


def test_out_of_sample_insufficient_data_when_too_few_trades(monkeypatch, isolated):
    class FakePeriod:
        def __init__(self, label, trades):
            self.label = label
            self.total_return_percent = 5.0
            self.sharpe_ratio = 0.5
            self.number_of_trades = trades
            self.error = None

    class FakeOOSResult:
        periods = [FakePeriod("IN_SAMPLE", 10), FakePeriod("OUT_OF_SAMPLE", 1)]

    monkeypatch.setattr(sc, "run_out_of_sample_validation", lambda **kw: FakeOOSResult())

    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    dim = next(d for d in result.dimensions if d.name == "OUT_OF_SAMPLE_STRENGTH")
    assert dim.label == "INSUFFICIENT_DATA"


def test_robustness_weak_when_mostly_low_robustness(monkeypatch, isolated):
    class FakeParam:
        def __init__(self, robustness):
            self.robustness = robustness

    class FakeResult:
        parameters = [FakeParam("LOW_ROBUSTNESS"), FakeParam("LOW_ROBUSTNESS"), FakeParam("HIGHER_ROBUSTNESS")]

    monkeypatch.setattr(sc, "run_sensitivity_analysis", lambda **kw: FakeResult())

    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    dim = next(d for d in result.dimensions if d.name == "ROBUSTNESS")
    assert dim.label == "WEAK"


def test_robustness_insufficient_data_when_all_inert(monkeypatch, isolated):
    class FakeParam:
        def __init__(self, robustness):
            self.robustness = robustness

    class FakeResult:
        parameters = [FakeParam("PARAMETER_INERT"), FakeParam("PARAMETER_INERT")]

    monkeypatch.setattr(sc, "run_sensitivity_analysis", lambda **kw: FakeResult())

    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    dim = next(d for d in result.dimensions if d.name == "ROBUSTNESS")
    assert dim.label == "INSUFFICIENT_DATA"


def test_walk_forward_insufficient_data_with_few_folds(monkeypatch, isolated):
    class FakeResult:
        folds = [object(), object()]
        folds_with_positive_return = 1

    monkeypatch.setattr(sc, "run_walk_forward", lambda **kw: FakeResult())

    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    dim = next(d for d in result.dimensions if d.name == "WALK_FORWARD_STABILITY")
    assert dim.label == "INSUFFICIENT_DATA"


def test_walk_forward_strong_when_most_folds_positive(isolated):
    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    dim = next(d for d in result.dimensions if d.name == "WALK_FORWARD_STABILITY")
    assert dim.label == "STRONG"


def test_regime_dependency_weak_when_negative_in_most_regimes(monkeypatch, isolated):
    class FakeBucket:
        def __init__(self, regime, trading_days, ret):
            self.regime = regime
            self.trading_days = trading_days
            self.compounded_return_percent = ret

    class FakeResult:
        buckets = [FakeBucket("BULL", 100, 12.0), FakeBucket("BEAR", 80, -5.0), FakeBucket("SIDEWAYS", 60, -2.0)]

    monkeypatch.setattr(sc, "compute_regime_performance", lambda *a, **kw: FakeResult())

    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    dim = next(d for d in result.dimensions if d.name == "REGIME_DEPENDENCY")
    assert dim.label == "WEAK"


def test_regime_dependency_moderate_when_mixed(isolated):
    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    dim = next(d for d in result.dimensions if d.name == "REGIME_DEPENDENCY")
    assert dim.label == "MODERATE"


def test_regime_dependency_strong_when_positive_across_regimes(monkeypatch, isolated):
    class FakeBucket:
        def __init__(self, regime, trading_days, ret):
            self.regime = regime
            self.trading_days = trading_days
            self.compounded_return_percent = ret

    class FakeResult:
        buckets = [FakeBucket("BULL", 100, 12.0), FakeBucket("BEAR", 50, 3.0)]

    monkeypatch.setattr(sc, "compute_regime_performance", lambda *a, **kw: FakeResult())

    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
    )
    dim = next(d for d in result.dimensions if d.name == "REGIME_DEPENDENCY")
    assert dim.label == "STRONG"


def test_forward_paper_not_provided_when_no_portfolio_id(isolated):
    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
        forward_portfolio_id=None,
    )
    dim = next(d for d in result.dimensions if d.name == "FORWARD_PAPER_DATA")
    assert dim.label == "NOT_PROVIDED"


def test_forward_paper_insufficient_data_with_thin_sample(monkeypatch, isolated):
    class FakeForwardView:
        trading_days_observed = 3
        total_return_percent = 1.0
        benchmark_return_percent = 0.5

    monkeypatch.setattr(sc.forward_validation, "get_forward_validation", lambda pid: FakeForwardView())

    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
        forward_portfolio_id="some_portfolio",
    )
    dim = next(d for d in result.dimensions if d.name == "FORWARD_PAPER_DATA")
    assert dim.label == "INSUFFICIENT_DATA"


def test_forward_paper_moderate_with_enough_days(monkeypatch, isolated):
    class FakeForwardView:
        trading_days_observed = 30
        total_return_percent = 4.0
        benchmark_return_percent = 2.0

    monkeypatch.setattr(sc.forward_validation, "get_forward_validation", lambda pid: FakeForwardView())

    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=isolated, benchmark="SPY", benchmark_full_price_df=isolated,
        forward_portfolio_id="some_portfolio",
    )
    dim = next(d for d in result.dimensions if d.name == "FORWARD_PAPER_DATA")
    assert dim.label == "MODERATE"


def test_short_history_produces_insufficient_data_for_oos_and_robustness(monkeypatch, ohlcv_short):
    # ohlcv_short is only 10 business days - far below the 90-day threshold
    # for both the out-of-sample split and the sensitivity sweep.
    result = sc.build_model_scorecard(
        ticker="TEST", full_price_df=ohlcv_short, benchmark="SPY", benchmark_full_price_df=ohlcv_short,
    )
    oos_dim = next(d for d in result.dimensions if d.name == "OUT_OF_SAMPLE_STRENGTH")
    robustness_dim = next(d for d in result.dimensions if d.name == "ROBUSTNESS")
    assert oos_dim.label == "INSUFFICIENT_DATA"
    assert robustness_dim.label == "INSUFFICIENT_DATA"
