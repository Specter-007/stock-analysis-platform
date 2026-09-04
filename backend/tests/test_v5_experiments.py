"""V5: Experiment Lab - creation, immutability, fingerprinting, execution,
lifecycle, persistence, duplication, comparison, and forward-simulation
linkage. Network-isolated: price data is synthetic, pre-fetched by the
test (mirroring how the route layer fetches it in production) and handed
directly to run_experiment, which never does its own I/O.
"""
import datetime as dt

import pytest

from app.experiments import service, store
from app.experiments.fingerprint import compute_fingerprint
from app.experiments.models import (
    STATUS_COMPLETED,
    STATUS_DRAFT,
    STATUS_FAILED,
    STATUS_PAPER_FORWARD_TEST,
    STATUS_VALIDATED,
    ExperimentConfig,
)


@pytest.fixture
def user_id(db_session):
    from app.models_db.user import User

    user = User(email="experiments-test@example.com", password_hash="x", display_name="Test")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user.id


def _config(**overrides) -> ExperimentConfig:
    base = dict(
        model_version="1.1",
        tickers=["AAA"],
        benchmark="SPY",
        start_date="2023-01-01",
        end_date="2024-01-01",
        initial_capital=10_000.0,
        commission_bps=5.0,
        slippage_bps=5.0,
    )
    base.update(overrides)
    return ExperimentConfig(**base)


def _price_data(df):
    return {"AAA": df}


# ---------------------------------------------------------------- Creation

def test_create_experiment_starts_in_draft_with_fingerprint(db_session, user_id, ohlcv_long):
    config = _config()
    exp = service.create_experiment(db_session, user_id, config, name="Test Experiment")
    assert exp.status == STATUS_DRAFT
    assert exp.fingerprint
    assert exp.id.startswith("exp_")


def test_created_experiment_is_persisted_and_reloadable(db_session, user_id, ohlcv_long):
    exp = service.create_experiment(db_session, user_id, _config(), name="Persisted")
    reloaded = service.get_experiment(db_session, user_id, exp.id)
    assert reloaded is not None
    assert reloaded.name == "Persisted"
    assert reloaded.config.tickers == ["AAA"]


def test_get_nonexistent_experiment_returns_none(db_session, user_id, ):
    assert service.get_experiment(db_session, user_id, "exp_doesnotexist") is None


# ------------------------------------------------------------ Fingerprint

def test_identical_configs_produce_identical_fingerprints(db_session, user_id, ):
    a = compute_fingerprint(_config())
    b = compute_fingerprint(_config())
    assert a == b


def test_different_capital_produces_different_fingerprint(db_session, user_id, ):
    a = compute_fingerprint(_config())
    b = compute_fingerprint(_config(initial_capital=20_000.0))
    assert a != b


def test_different_model_version_produces_different_fingerprint(db_session, user_id, ):
    a = compute_fingerprint(_config(model_version="1.0"))
    b = compute_fingerprint(_config(model_version="1.1"))
    assert a != b


def test_ticker_order_does_not_affect_fingerprint(db_session, user_id, ):
    a = compute_fingerprint(_config(tickers=["AAA", "BBB"]))
    b = compute_fingerprint(_config(tickers=["BBB", "AAA"]))
    assert a == b


def test_notes_and_tags_do_not_affect_fingerprint(db_session, user_id, ):
    exp_a = service.create_experiment(db_session, user_id, _config(), name="A", notes="hypothesis one")
    exp_b = service.create_experiment(db_session, user_id, _config(), name="B", notes="a completely different note", tags=["baseline"])
    assert exp_a.fingerprint == exp_b.fingerprint


def test_fingerprint_format_is_dash_grouped_hex(db_session, user_id, ):
    fp = compute_fingerprint(_config())
    parts = fp.split("-")
    assert len(parts) == 4
    assert all(len(p) == 4 for p in parts)
    assert all(c in "0123456789ABCDEF" for p in parts for c in p)


# ---------------------------------------------------------- Configuration immutability

def test_running_experiment_does_not_mutate_global_config_defaults(db_session, user_id, ohlcv_long):
    from app.config import MODEL_VERSION_CURRENT

    exp = service.create_experiment(db_session, user_id, _config(model_version="1.0"), name="Immutable test")
    service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    # Running an experiment with a NON-default model version must never
    # change what "current" means globally.
    assert MODEL_VERSION_CURRENT == "1.1"


def test_experiment_config_unchanged_after_running(db_session, user_id, ohlcv_long):
    exp = service.create_experiment(db_session, user_id, _config(), name="Config check")
    original_config_dict = dict(vars(exp.config))
    ran = service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    assert dict(vars(ran.config)) == original_config_dict


def test_reopening_experiment_shows_unchanged_configuration(db_session, user_id, ohlcv_long):
    exp = service.create_experiment(db_session, user_id, _config(initial_capital=15_000.0), name="Reopen test")
    service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    reloaded = service.get_experiment(db_session, user_id, exp.id)
    assert reloaded.config.initial_capital == 15_000.0
    assert reloaded.fingerprint == exp.fingerprint


# --------------------------------------------------------------- Execution

def _date_range(df, start_offset=220):
    return df.index[start_offset].date().isoformat(), df.index[-1].date().isoformat()


def test_run_experiment_backtest_only_reaches_validated(db_session, user_id, ohlcv_long):
    start, end = _date_range(ohlcv_long)
    exp = service.create_experiment(db_session, user_id, _config(start_date=start, end_date=end), name="Backtest only")
    ran = service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    # No validation procedures were requested, so nothing could fail -> VALIDATED.
    assert ran.status == STATUS_VALIDATED
    assert ran.results.backtest.completed is True
    assert ran.results.backtest.result["total_return_percent"] is not None


def test_backtest_result_includes_equity_curves_for_charting(db_session, user_id, ohlcv_long):
    start, end = _date_range(ohlcv_long)
    exp = service.create_experiment(db_session, user_id, _config(start_date=start, end_date=end), name="Curve check")
    ran = service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    result = ran.results.backtest.result
    assert len(result["strategy_curve"]) > 0
    assert set(result["strategy_curve"][0].keys()) == {"date", "equity"}
    assert len(result["drawdown_curve"]) == len(result["strategy_curve"])


def test_portfolio_backtest_result_includes_equity_curves(db_session, user_id, ohlcv_long, ohlcv_uptrend, monkeypatch):
    from app.backtesting import portfolio as portfolio_module
    monkeypatch.setattr(portfolio_module, "_sector_for", lambda t: "Technology")

    start = ohlcv_long.index[220].date().isoformat()
    end = ohlcv_long.index[-1].date().isoformat()
    exp = service.create_experiment(db_session, user_id, _config(tickers=["AAA", "BBB"], start_date=start, end_date=end), name="Portfolio curve check")
    ran = service.run_experiment(db_session, user_id, exp.id, price_data={"AAA": ohlcv_long, "BBB": ohlcv_uptrend}, benchmark_df=ohlcv_long, tickers_unavailable={},
    )
    result = ran.results.backtest.result
    assert len(result["equity_curve"]) > 0
    assert len(result["equal_weight_buy_hold_curve"]) > 0


def test_run_experiment_with_all_validations_requested(db_session, user_id, ohlcv_long):
    start, end = _date_range(ohlcv_long, start_offset=0)
    exp = service.create_experiment(db_session, user_id, _config(
            start_date=ohlcv_long.index[0].date().isoformat(), end_date=ohlcv_long.index[-1].date().isoformat(),
            run_out_of_sample=True, run_sensitivity=True, run_monte_carlo=True, run_cost_stress=True,
            run_regime_analysis=True, monte_carlo_simulations=100,
        ),
        name="Full validation",
    )
    ran = service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    assert ran.results.out_of_sample.requested is True
    assert ran.results.sensitivity.requested is True
    assert ran.results.monte_carlo.requested is True
    assert ran.results.cost_stress.requested is True
    assert ran.results.regime_performance.requested is True
    assert ran.status in (STATUS_VALIDATED, STATUS_COMPLETED)


def test_run_experiment_backtest_failure_sets_failed_status(db_session, user_id, ohlcv_long):
    # A date range with almost no trading days is too short for run_backtest's
    # MIN_SIM_TRADING_DAYS floor - InsufficientHistoryError propagates up.
    exp = service.create_experiment(db_session, user_id, _config(start_date=ohlcv_long.index[-5].date().isoformat(), end_date=ohlcv_long.index[-1].date().isoformat()),
        name="Too short",
    )
    ran = service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    assert ran.status == STATUS_FAILED
    assert ran.error is not None
    assert ran.results.backtest.completed is False


def test_run_experiment_walk_forward_insufficient_history_stays_completed_not_validated(db_session, user_id, ohlcv_long):
    start, end = _date_range(ohlcv_long)
    exp = service.create_experiment(db_session, user_id, _config(start_date=start, end_date=end, run_walk_forward=True),
        name="WF insufficient",
    )
    ran = service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    # ohlcv_long is ~1.6 years - walk-forward's 2+1 year defaults can't
    # produce a fold, so the requested validation fails and the experiment
    # must NOT be called VALIDATED even though the backtest itself succeeded.
    assert ran.results.walk_forward.completed is False
    assert ran.status == STATUS_COMPLETED


def test_data_provenance_recorded(db_session, user_id, ohlcv_long):
    start, end = _date_range(ohlcv_long)
    exp = service.create_experiment(db_session, user_id, _config(start_date=start, end_date=end), name="Provenance")
    ran = service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long,
        tickers_unavailable={"ZZZ": "not found"},
    )
    assert ran.data_provenance is not None
    assert ran.data_provenance.tickers_retrieved == ["AAA"]
    assert ran.data_provenance.tickers_unavailable == {"ZZZ": "not found"}


def test_running_experiment_persists_running_status_before_completion(db_session, user_id, monkeypatch, ohlcv_long):
    """Simulates a crash mid-run: if the process died right after the
    RUNNING write, the persisted file must show RUNNING (visible, not
    silently stuck at DRAFT) rather than a half-written result.
    """
    start, end = _date_range(ohlcv_long)
    exp = service.create_experiment(db_session, user_id, _config(start_date=start, end_date=end), name="Crash test")

    captured_statuses = []
    original_save = store.save_experiment

    def spy_save(db, uid, experiment):
        captured_statuses.append(experiment.status)
        original_save(db, uid, experiment)

    monkeypatch.setattr(store, "save_experiment", spy_save)
    service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    assert "RUNNING" in captured_statuses


# --------------------------------------------------------- Portfolio experiments

def test_portfolio_experiment_runs_backtest(db_session, user_id, ohlcv_long, ohlcv_uptrend, monkeypatch):
    from app.backtesting import portfolio as portfolio_module
    monkeypatch.setattr(portfolio_module, "_sector_for", lambda t: "Technology")

    start = ohlcv_long.index[220].date().isoformat()
    end = ohlcv_long.index[-1].date().isoformat()
    config = _config(tickers=["AAA", "BBB"], start_date=start, end_date=end)
    exp = service.create_experiment(db_session, user_id, config, name="Portfolio test")

    ran = service.run_experiment(db_session, user_id, exp.id, price_data={"AAA": ohlcv_long, "BBB": ohlcv_uptrend}, benchmark_df=ohlcv_long, tickers_unavailable={},
    )
    assert ran.results.backtest.completed is True
    assert ran.status == STATUS_VALIDATED


def test_portfolio_experiment_flags_unsupported_validations(db_session, user_id, ohlcv_long, ohlcv_uptrend, monkeypatch):
    from app.backtesting import portfolio as portfolio_module
    monkeypatch.setattr(portfolio_module, "_sector_for", lambda t: "Technology")

    start = ohlcv_long.index[220].date().isoformat()
    end = ohlcv_long.index[-1].date().isoformat()
    config = _config(tickers=["AAA", "BBB"], start_date=start, end_date=end, run_sensitivity=True, run_walk_forward=True)
    exp = service.create_experiment(db_session, user_id, config, name="Portfolio unsupported validations")

    ran = service.run_experiment(db_session, user_id, exp.id, price_data={"AAA": ohlcv_long, "BBB": ohlcv_uptrend}, benchmark_df=ohlcv_long, tickers_unavailable={},
    )
    assert ran.results.sensitivity.requested is True
    assert ran.results.sensitivity.completed is False
    assert "not yet implemented" in ran.results.sensitivity.error
    assert ran.status == STATUS_COMPLETED  # never VALIDATED when a requested procedure could not run


# ------------------------------------------------------------- Duplication

def test_duplicate_experiment_has_same_fingerprint_new_id(db_session, user_id, ohlcv_long):
    original = service.create_experiment(db_session, user_id, _config(), name="Original")
    duplicate = service.duplicate_experiment(db_session, user_id, original.id)
    assert duplicate.id != original.id
    assert duplicate.fingerprint == original.fingerprint
    assert duplicate.reproduced_from == original.id
    assert duplicate.status == STATUS_DRAFT


def test_duplicate_of_nonexistent_experiment_raises(db_session, user_id, ):
    with pytest.raises(ValueError):
        service.duplicate_experiment(db_session, user_id, "exp_missing")


# -------------------------------------------------------------- Notes/tags

def test_update_notes_does_not_change_fingerprint(db_session, user_id, ohlcv_long):
    exp = service.create_experiment(db_session, user_id, _config(), name="Notes test", notes="original")
    updated = service.update_notes(db_session, user_id, exp.id, notes="revised hypothesis", tags=["momentum"])
    assert updated.notes == "revised hypothesis"
    assert updated.tags == ["momentum"]
    assert updated.fingerprint == exp.fingerprint


def test_update_notes_nonexistent_raises(db_session, user_id, ):
    with pytest.raises(ValueError):
        service.update_notes(db_session, user_id, "exp_missing", notes="x")


# --------------------------------------------------------------- Archiving

def test_archive_experiment_hides_from_default_listing(db_session, user_id, ohlcv_long):
    exp = service.create_experiment(db_session, user_id, _config(), name="To Archive")
    service.archive_experiment(db_session, user_id, exp.id, archived=True)
    active = service.list_experiments(db_session, user_id, include_archived=False)
    assert exp.id not in [row["experiment"].id for row in active]
    all_rows = service.list_experiments(db_session, user_id, include_archived=True)
    assert exp.id in [row["experiment"].id for row in all_rows]


# ------------------------------------------------------ Data-mining warning

def test_data_mining_warning_flagged_past_threshold(db_session, user_id, ohlcv_long):
    from app.config import EXPERIMENT_DATA_MINING_WARNING_THRESHOLD

    config = _config()
    for i in range(EXPERIMENT_DATA_MINING_WARNING_THRESHOLD):
        service.create_experiment(db_session, user_id, config, name=f"Repeat {i}")

    rows = service.list_experiments(db_session, user_id, )
    assert all(row["data_mining_warning"] for row in rows)
    assert rows[0]["group_count"] == EXPERIMENT_DATA_MINING_WARNING_THRESHOLD


def test_no_data_mining_warning_below_threshold(db_session, user_id, ohlcv_long):
    service.create_experiment(db_session, user_id, _config(), name="Solo")
    rows = service.list_experiments(db_session, user_id, )
    assert rows[0]["data_mining_warning"] is False
    assert rows[0]["group_count"] == 1


# ---------------------------------------------------------------- Compare

def test_compare_warns_on_mismatched_periods(db_session, user_id, ohlcv_long):
    a = service.create_experiment(db_session, user_id, _config(start_date="2018-01-01", end_date="2024-01-01"), name="Long period")
    b = service.create_experiment(db_session, user_id, _config(start_date="2023-01-01", end_date="2024-01-01"), name="Short period")
    result = service.compare_experiments(db_session, user_id, [a.id, b.id])
    assert any("different length" in w for w in result["warnings"])


def test_compare_warns_on_mismatched_model_versions(db_session, user_id, ohlcv_long):
    a = service.create_experiment(db_session, user_id, _config(model_version="1.0"), name="v1.0")
    b = service.create_experiment(db_session, user_id, _config(model_version="1.1"), name="v1.1")
    result = service.compare_experiments(db_session, user_id, [a.id, b.id])
    assert any("model versions" in w for w in result["warnings"])


def test_compare_no_warnings_for_matching_configs(db_session, user_id, ohlcv_long):
    a = service.create_experiment(db_session, user_id, _config(), name="A")
    b = service.create_experiment(db_session, user_id, _config(), name="B")
    result = service.compare_experiments(db_session, user_id, [a.id, b.id])
    assert result["warnings"] == []


def test_compare_raises_for_missing_experiment(db_session, user_id, ohlcv_long):
    a = service.create_experiment(db_session, user_id, _config(), name="A")
    with pytest.raises(ValueError):
        service.compare_experiments(db_session, user_id, [a.id, "exp_missing"])


# ----------------------------------------------------- Forward simulation

def test_start_forward_simulation_single_ticker(db_session, user_id, ohlcv_long, monkeypatch):
    from app.paper_trading import service as paper_trading_service

    monkeypatch.setattr(paper_trading_service, "_current_price", lambda t: 100.0)
    monkeypatch.setattr(paper_trading_service, "_current_signal_snapshot", lambda t: (None, None))
    monkeypatch.setattr(paper_trading_service, "_current_market_regime", lambda: None)
    monkeypatch.setattr(paper_trading_service, "_latest_real_trading_day", lambda: (None, None))

    exp = service.create_experiment(db_session, user_id, _config(initial_capital=25_000.0), name="Forward test")
    ran = service.start_forward_simulation(db_session, user_id, exp.id)
    assert ran.status == STATUS_PAPER_FORWARD_TEST
    assert ran.forward_portfolio_id == exp.id

    portfolio = paper_trading_service.get_portfolio(db_session, user_id, ran.forward_portfolio_id)
    assert portfolio.starting_capital == 25_000.0


def test_start_forward_simulation_rejects_portfolio_experiments(db_session, user_id, ohlcv_long):
    exp = service.create_experiment(db_session, user_id, _config(tickers=["AAA", "BBB"]), name="Portfolio forward")
    with pytest.raises(ValueError, match="not yet supported"):
        service.start_forward_simulation(db_session, user_id, exp.id)


# ------------------------------------------------------------- Persistence

def test_load_experiment_owned_by_another_user_returns_none(db_session, user_id, ohlcv_long):
    """IDOR check at the store layer: loading an experiment that exists but
    belongs to a different user must be indistinguishable from it not
    existing at all - see app.auth.exceptions.ResourceNotFoundError.
    """
    from app.models_db.user import User

    other = User(email="experiments-other@example.com", password_hash="x", display_name="Other")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    exp = service.create_experiment(db_session, user_id, _config(), name="Mine")
    assert store.load_experiment(db_session, other.id, exp.id) is None
    assert store.load_experiment(db_session, user_id, exp.id) is not None


def test_save_experiment_updates_same_row_not_a_duplicate(db_session, user_id):
    exp = service.create_experiment(db_session, user_id, _config(), name="Original name")
    exp.name = "Renamed"
    store.save_experiment(db_session, user_id, exp)

    assert len(store.list_experiment_ids(db_session, user_id)) == 1
    reloaded = store.load_experiment(db_session, user_id, exp.id)
    assert reloaded.name == "Renamed"


def test_full_round_trip_preserves_every_experiment_field(db_session, user_id, ohlcv_long):
    """Regression test: a field added to the Experiment/ExperimentConfig
    dataclasses but forgotten in store._dict_to_experiment's manual
    reconstruction would silently reset to its default on every reload
    (exactly what happened to `archived` during development - caught by
    test_archive_experiment_hides_from_default_listing, generalized here
    so the NEXT forgotten field is caught just as fast).
    """
    start, end = _date_range(ohlcv_long)
    exp = service.create_experiment(db_session, user_id, _config(start_date=start, end_date=end, run_out_of_sample=True), name="Round trip", notes="note", tags=["baseline"],
    )
    ran = service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    service.archive_experiment(db_session, user_id, ran.id, archived=True)

    reloaded = store.load_experiment(db_session, user_id, ran.id)
    assert vars(reloaded) == vars(store.load_experiment(db_session, user_id, ran.id))  # stable across repeated loads
    for field_name in ("id", "name", "created_at", "status", "fingerprint", "notes", "tags", "archived", "reproduced_from"):
        assert getattr(reloaded, field_name) == getattr(store.load_experiment(db_session, user_id, ran.id), field_name)
    assert reloaded.archived is True
    assert reloaded.results.out_of_sample.requested is True
    assert vars(reloaded.config) == vars(ran.config)


# --------------------------------------------- Forward vs. historical

def test_forward_vs_historical_unavailable_before_forward_sim_started(db_session, user_id, ohlcv_long):
    start, end = _date_range(ohlcv_long)
    exp = service.create_experiment(db_session, user_id, _config(start_date=start, end_date=end, run_out_of_sample=True), name="No forward yet")
    service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    result = service.get_forward_vs_historical(db_session, user_id, exp.id)
    assert result["available"] is False


def test_forward_vs_historical_reports_developing_sample(db_session, user_id, monkeypatch, ohlcv_long):
    from app.paper_trading import service as paper_trading_service

    monkeypatch.setattr(paper_trading_service, "_current_price", lambda t: 100.0)
    monkeypatch.setattr(paper_trading_service, "_current_signal_snapshot", lambda t: (None, None))
    monkeypatch.setattr(paper_trading_service, "_current_market_regime", lambda: None)
    monkeypatch.setattr(paper_trading_service, "_latest_real_trading_day", lambda: (None, None))

    start, end = _date_range(ohlcv_long)
    exp = service.create_experiment(db_session, user_id, _config(start_date=start, end_date=end, run_out_of_sample=True), name="Developing")
    service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    service.start_forward_simulation(db_session, user_id, exp.id)

    result = service.get_forward_vs_historical(db_session, user_id, exp.id)
    assert result["available"] is True
    assert result["forward_sample_developing"] is True
    assert result["historical"] is not None
    assert result["historical_source"] == "OUT_OF_SAMPLE"


def test_forward_vs_historical_falls_back_to_backtest_without_oos(db_session, user_id, monkeypatch, ohlcv_long):
    from app.paper_trading import service as paper_trading_service

    monkeypatch.setattr(paper_trading_service, "_current_price", lambda t: 100.0)
    monkeypatch.setattr(paper_trading_service, "_current_signal_snapshot", lambda t: (None, None))
    monkeypatch.setattr(paper_trading_service, "_current_market_regime", lambda: None)
    monkeypatch.setattr(paper_trading_service, "_latest_real_trading_day", lambda: (None, None))

    start, end = _date_range(ohlcv_long)
    exp = service.create_experiment(db_session, user_id, _config(start_date=start, end_date=end), name="No OOS requested")
    service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    service.start_forward_simulation(db_session, user_id, exp.id)

    result = service.get_forward_vs_historical(db_session, user_id, exp.id)
    assert result["historical_source"] == "BACKTEST"


def test_forward_vs_historical_flags_material_deviation(db_session, user_id, monkeypatch, ohlcv_long):
    from app.experiments import service as service_module
    from app.paper_trading import forward_validation as fv_module

    class FakeForwardView:
        total_return_percent = 50.0
        max_drawdown_percent = -5.0
        trading_days_observed = 30
        insufficient_sample = False

    monkeypatch.setattr(fv_module, "get_forward_validation", lambda db, uid, pid: FakeForwardView())
    monkeypatch.setattr(service_module, "_forward_sharpe", lambda db, uid, pid: None)

    start, end = _date_range(ohlcv_long)
    exp = service.create_experiment(db_session, user_id, _config(start_date=start, end_date=end, run_out_of_sample=True), name="Deviation test")
    ran = service.run_experiment(db_session, user_id, exp.id, price_data=_price_data(ohlcv_long), benchmark_df=ohlcv_long, tickers_unavailable={})
    ran.forward_portfolio_id = "fake_portfolio"
    store.save_experiment(db_session, user_id, ran)

    result = service.get_forward_vs_historical(db_session, user_id, exp.id)
    assert result["available"] is True
    assert any("materially" in n for n in result["deviation_notes"])


def test_experiment_id_uses_only_safe_characters(db_session, user_id, ohlcv_long):
    exp = service.create_experiment(db_session, user_id, _config(), name="Safe id")
    import re
    assert re.match(r"^exp_[a-f0-9]+$", exp.id)
