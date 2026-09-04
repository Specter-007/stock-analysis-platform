"""V5: Experiment Lab orchestration.

Ties together the already-existing, already-tested engines (single-ticker
and portfolio backtesting, out-of-sample validation, walk-forward,
sensitivity, Monte Carlo, regime-conditioned performance, cost stress) into
one reproducible research record. This module adds NO new backtesting or
scoring logic of its own - every number in an experiment's results comes
from calling exactly the same function the corresponding standalone page
already calls. Running an experiment never mutates global model defaults,
other experiments, or any other persisted state - it only reads the
price/benchmark data handed to it and writes its own experiment file.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict

import pandas as pd

from app.backtesting.cost_stress import run_cost_stress_test
from app.backtesting.engine import run_backtest
from app.backtesting.monte_carlo import run_monte_carlo
from app.backtesting.out_of_sample import run_out_of_sample_validation
from app.backtesting.portfolio import PortfolioConstraints, run_portfolio_backtest
from app.backtesting.sensitivity import run_sensitivity_analysis
from app.backtesting.walk_forward import run_walk_forward
from app.config import EXPERIMENT_DATA_MINING_WARNING_THRESHOLD
from app.experiments import store
from app.experiments.fingerprint import compute_fingerprint
from app.experiments.models import (
    STATUS_COMPLETED,
    STATUS_DRAFT,
    STATUS_FAILED,
    STATUS_PAPER_FORWARD_TEST,
    STATUS_RUNNING,
    STATUS_VALIDATED,
    DataProvenance,
    Experiment,
    ExperimentConfig,
    ExperimentResults,
    ValidationOutcome,
)
from app.backtesting import metrics as backtest_metrics
from app.market.regime_performance import compute_regime_performance
from app.paper_trading import forward_validation
from app.paper_trading import service as paper_trading_service
from app.services.exceptions import InsufficientHistoryError
from app.utils import timeutils

# A plain, disclosed percentage-point threshold - the same "documented
# heuristic, not a hypothesis test" philosophy used by model drift
# detection (app.model_evaluation.drift): forward paper-trading and
# historical backtest returns are each single realized paths, not
# repeated-trial samples, so no classical significance test applies here
# either.
FORWARD_DEVIATION_MATERIAL_THRESHOLD_PP = 10.0

FORWARD_SIM_UNSUPPORTED_MESSAGE = (
    "Forward paper simulation is not yet supported for multi-ticker portfolio experiments - "
    "only single-ticker experiments can start a forward simulation in this version. This is a "
    "documented limitation, not an oversight: the paper-trading engine trades one ticker per "
    "order and has no portfolio-level allocation/rebalancing forward engine yet."
)

_NOT_APPLICABLE_FOR_PORTFOLIO = (
    "This validation procedure operates on the single-ticker backtest engine's own trade/curve "
    "objects and is not yet implemented for multi-ticker portfolio experiments."
)


def _now_iso() -> str:
    return timeutils.to_iso(timeutils.utc_now())


def create_experiment(config: ExperimentConfig, name: str, notes: str = "", tags: list[str] | None = None) -> Experiment:
    now = _now_iso()
    experiment = Experiment(
        id=store.new_experiment_id(),
        name=name,
        created_at=now,
        updated_at=now,
        status=STATUS_DRAFT,
        config=config,
        fingerprint=compute_fingerprint(config),
        notes=notes,
        tags=list(tags or []),
    )
    store.save_experiment(experiment)
    return experiment


def get_experiment(experiment_id: str) -> Experiment | None:
    return store.load_experiment(experiment_id)


def delete_experiment(experiment_id: str) -> bool:
    return store.delete_experiment(experiment_id)


def archive_experiment(experiment_id: str, archived: bool = True) -> Experiment:
    experiment = store.load_experiment(experiment_id)
    if experiment is None:
        raise ValueError(f"Experiment not found: {experiment_id}")
    experiment.archived = archived
    experiment.updated_at = _now_iso()
    store.save_experiment(experiment)
    return experiment


def duplicate_experiment(source_id: str, new_name: str | None = None) -> Experiment:
    source = store.load_experiment(source_id)
    if source is None:
        raise ValueError(f"Experiment not found: {source_id}")
    now = _now_iso()
    duplicate = Experiment(
        id=store.new_experiment_id(),
        name=new_name or f"{source.name} (copy)",
        created_at=now,
        updated_at=now,
        status=STATUS_DRAFT,
        config=ExperimentConfig(**asdict(source.config)),
        fingerprint=source.fingerprint,  # identical config -> identical fingerprint, by design
        notes=source.notes,
        tags=list(source.tags),
        reproduced_from=source.id,
    )
    store.save_experiment(duplicate)
    return duplicate


def _group_key(config: ExperimentConfig) -> str:
    return "|".join([",".join(sorted(config.tickers)), config.start_date, config.end_date])


def list_experiments(include_archived: bool = False) -> list[dict]:
    """Returns each experiment alongside its research-history group's
    experiment count, so a caller reusing the same (universe, period) many
    times over is visible rather than hidden - see EXPERIMENT_DATA_MINING_
    WARNING_THRESHOLD. This never blocks or corrects the behavior; it only
    discloses it.
    """
    experiments = store.list_experiments()
    if not include_archived:
        experiments = [e for e in experiments if not e.archived]

    group_counts: dict[str, int] = {}
    for e in experiments:
        key = _group_key(e.config)
        group_counts[key] = group_counts.get(key, 0) + 1

    experiments.sort(key=lambda e: e.created_at, reverse=True)

    return [
        {
            "experiment": e,
            "group_count": group_counts[_group_key(e.config)],
            "data_mining_warning": group_counts[_group_key(e.config)] >= EXPERIMENT_DATA_MINING_WARNING_THRESHOLD,
        }
        for e in experiments
    ]


# ---------------------------------------------------------------- Running


def _backtest_summary(bt) -> dict:
    return {
        "final_capital": bt.final_capital,
        "total_return_percent": bt.total_return_percent,
        "annualized_return_percent": bt.annualized_return_percent,
        "buy_hold_return_percent": bt.buy_hold_return_percent,
        "benchmark_return_percent": bt.benchmark_return_percent,
        "max_drawdown_percent": bt.max_drawdown_percent,
        "sharpe_ratio": bt.sharpe_ratio,
        "trading_days": bt.trading_days,
        "warnings": bt.warnings,
        **bt.trade_stats,
        **bt.advanced_metrics,
    }


def _portfolio_backtest_summary(bt) -> dict:
    return {
        "final_capital": bt.final_capital,
        "total_return_percent": bt.total_return_percent,
        "equal_weight_buy_hold_return_percent": bt.equal_weight_buy_hold_return_percent,
        "benchmark_return_percent": bt.benchmark_return_percent,
        "max_drawdown_percent": bt.max_drawdown_percent,
        "sharpe_ratio": bt.sharpe_ratio,
        "trading_days": bt.trading_days,
        "number_of_rebalances": bt.number_of_rebalances,
        "warnings": bt.warnings,
        "excluded_tickers": bt.excluded_tickers,
        "risk_analytics": bt.risk_analytics,
        **bt.advanced_metrics,
    }


def _split_into_thirds(full_df: pd.DataFrame, start_date: dt.date, end_date: dt.date):
    mask = (full_df.index.date >= start_date) & (full_df.index.date <= end_date)
    dates = full_df.index[mask]
    n = len(dates)
    if n < 90:
        return None
    third = n // 3
    return [
        ("IN_SAMPLE", dates[0].date(), dates[third].date()),
        ("VALIDATION", dates[third + 1].date(), dates[2 * third].date()),
        ("OUT_OF_SAMPLE", dates[2 * third + 1].date(), dates[-1].date()),
    ]


def _run_out_of_sample(ticker: str, full_df: pd.DataFrame, start_date: dt.date, end_date: dt.date, config: ExperimentConfig) -> ValidationOutcome:
    windows = _split_into_thirds(full_df, start_date, end_date)
    if windows is None:
        return ValidationOutcome(requested=True, completed=False, error="Not enough history in the requested period to split into in-sample/validation/out-of-sample thirds.")
    try:
        result = run_out_of_sample_validation(
            ticker=ticker, full_price_df=full_df, windows=windows,
            initial_capital=config.initial_capital, transaction_cost_bps=config.commission_bps,
            slippage_bps=config.slippage_bps, model_version=config.model_version,
        )
        any_error = any(p.error for p in result.periods)
        return ValidationOutcome(
            requested=True, completed=not any_error,
            result={"periods": [asdict(p) for p in result.periods]},
            error="One or more periods failed." if any_error else None,
        )
    except Exception as exc:
        return ValidationOutcome(requested=True, completed=False, error=str(exc))


def _run_walk_forward_validation(ticker: str, full_df: pd.DataFrame, config: ExperimentConfig) -> ValidationOutcome:
    try:
        result = run_walk_forward(
            ticker=ticker, full_price_df=full_df,
            train_years=config.walk_forward_train_years, test_years=config.walk_forward_test_years,
            max_folds=config.walk_forward_max_folds, initial_capital=config.initial_capital,
            transaction_cost_bps=config.commission_bps, slippage_bps=config.slippage_bps,
        )
        completed = len(result.folds) > 0
        return ValidationOutcome(
            requested=True, completed=completed,
            result={
                "folds": [asdict(f) for f in result.folds],
                "folds_with_positive_return": result.folds_with_positive_return,
                "average_test_return_percent": result.average_test_return_percent,
            },
            error=None if completed else "No walk-forward folds could be generated from the available history.",
        )
    except Exception as exc:
        return ValidationOutcome(requested=True, completed=False, error=str(exc))


def _run_sensitivity_validation(ticker: str, full_df: pd.DataFrame, start_date: dt.date, end_date: dt.date, config: ExperimentConfig) -> ValidationOutcome:
    try:
        result = run_sensitivity_analysis(
            ticker=ticker, full_price_df=full_df, start_date=start_date, end_date=end_date,
            initial_capital=config.initial_capital, transaction_cost_bps=config.commission_bps,
            slippage_bps=config.slippage_bps, model_version=config.model_version,
            parameters=tuple(config.sensitivity_parameters),
        )
        return ValidationOutcome(requested=True, completed=True, result={"parameters": [asdict(p) for p in result.parameters]})
    except InsufficientHistoryError as exc:
        return ValidationOutcome(requested=True, completed=False, error=str(exc))
    except Exception as exc:
        return ValidationOutcome(requested=True, completed=False, error=str(exc))


def _run_monte_carlo_validation(config: ExperimentConfig, bt) -> ValidationOutcome:
    try:
        equity_series = pd.Series({p.date: p.equity for p in bt.strategy_curve})
        daily_returns = equity_series.pct_change()
        mc = run_monte_carlo(
            trades=bt.trades, daily_returns=daily_returns, initial_capital=config.initial_capital,
            num_simulations=config.monte_carlo_simulations, seed=config.monte_carlo_seed,
            trading_days_in_period=bt.trading_days,
        )
        completed = mc.resampling_basis != "unavailable"
        return ValidationOutcome(
            requested=True, completed=completed, result=asdict(mc),
            error=None if completed else "No trade or daily-return sample was available to resample.",
        )
    except Exception as exc:
        return ValidationOutcome(requested=True, completed=False, error=str(exc))


def _run_regime_validation(ticker: str, benchmark: str, bt, benchmark_df: pd.DataFrame | None) -> ValidationOutcome:
    if benchmark_df is None or benchmark_df.empty:
        return ValidationOutcome(requested=True, completed=False, error="Benchmark data unavailable.")
    try:
        result = compute_regime_performance(ticker, benchmark, bt, benchmark_df)
        return ValidationOutcome(requested=True, completed=True, result={"buckets": [asdict(b) for b in result.buckets]})
    except Exception as exc:
        return ValidationOutcome(requested=True, completed=False, error=str(exc))


def _run_cost_stress_validation(ticker: str, full_df: pd.DataFrame, start_date: dt.date, end_date: dt.date, config: ExperimentConfig) -> ValidationOutcome:
    try:
        result = run_cost_stress_test(
            ticker=ticker, full_price_df=full_df, start_date=start_date, end_date=end_date,
            initial_capital=config.initial_capital, base_commission_bps=config.commission_bps,
            base_slippage_bps=config.slippage_bps, model_version=config.model_version,
        )
        return ValidationOutcome(requested=True, completed=result.gross_return_percent is not None, result=asdict(result))
    except Exception as exc:
        return ValidationOutcome(requested=True, completed=False, error=str(exc))


def run_experiment(
    experiment_id: str,
    price_data: dict[str, pd.DataFrame],
    benchmark_df: pd.DataFrame | None,
    tickers_unavailable: dict[str, str],
    data_source: str = "Yahoo Finance via yfinance",
    data_status: str = "HISTORICAL",
    latest_market_timestamp: str | None = None,
) -> Experiment:
    experiment = store.load_experiment(experiment_id)
    if experiment is None:
        raise ValueError(f"Experiment not found: {experiment_id}")

    experiment.status = STATUS_RUNNING
    experiment.updated_at = _now_iso()
    store.save_experiment(experiment)  # persisted immediately: a crash mid-run leaves this visible, not silently stuck at DRAFT

    config = experiment.config
    start_date = dt.date.fromisoformat(config.start_date)
    end_date = dt.date.fromisoformat(config.end_date)
    results = ExperimentResults()

    try:
        if config.is_portfolio:
            constraints = PortfolioConstraints(**(config.portfolio_constraints or {}))
            bt = run_portfolio_backtest(
                tickers=[t for t in config.tickers if t in price_data], price_data=price_data,
                start_date=start_date, end_date=end_date, initial_capital=config.initial_capital,
                transaction_cost_bps=config.commission_bps, slippage_bps=config.slippage_bps,
                allocation_method=config.allocation_method or "EQUAL_WEIGHT",
                rebalance_frequency=config.rebalance_frequency or "MONTHLY", constraints=constraints,
                model_version=config.model_version, benchmark_ticker=config.benchmark, benchmark_price_df=benchmark_df,
            )
            results.backtest = ValidationOutcome(requested=True, completed=True, result=_portfolio_backtest_summary(bt))
        else:
            ticker = config.tickers[0]
            bt = run_backtest(
                ticker=ticker, full_price_df=price_data[ticker], start_date=start_date, end_date=end_date,
                initial_capital=config.initial_capital, transaction_cost_bps=config.commission_bps,
                slippage_bps=config.slippage_bps, benchmark_ticker=config.benchmark,
                benchmark_full_price_df=benchmark_df, model_version=config.model_version,
            )
            results.backtest = ValidationOutcome(requested=True, completed=True, result=_backtest_summary(bt))
    except Exception as exc:
        results.backtest = ValidationOutcome(requested=True, completed=False, error=str(exc))
        experiment.results = results
        experiment.status = STATUS_FAILED
        experiment.error = f"Backtest failed: {exc}"
        experiment.updated_at = _now_iso()
        store.save_experiment(experiment)
        return experiment

    requested_and_outcomes: list[tuple[bool, ValidationOutcome]] = []

    if config.is_portfolio:
        for requested, name in [
            (config.run_out_of_sample, "out_of_sample"), (config.run_walk_forward, "walk_forward"),
            (config.run_sensitivity, "sensitivity"), (config.run_monte_carlo, "monte_carlo"),
            (config.run_regime_analysis, "regime_performance"), (config.run_cost_stress, "cost_stress"),
        ]:
            if requested:
                outcome = ValidationOutcome(requested=True, completed=False, error=_NOT_APPLICABLE_FOR_PORTFOLIO)
                setattr(results, name, outcome)
                requested_and_outcomes.append((True, outcome))
    else:
        ticker = config.tickers[0]
        full_df = price_data[ticker]

        if config.run_out_of_sample:
            results.out_of_sample = _run_out_of_sample(ticker, full_df, start_date, end_date, config)
            requested_and_outcomes.append((True, results.out_of_sample))
        if config.run_walk_forward:
            results.walk_forward = _run_walk_forward_validation(ticker, full_df, config)
            requested_and_outcomes.append((True, results.walk_forward))
        if config.run_sensitivity:
            results.sensitivity = _run_sensitivity_validation(ticker, full_df, start_date, end_date, config)
            requested_and_outcomes.append((True, results.sensitivity))
        if config.run_monte_carlo:
            results.monte_carlo = _run_monte_carlo_validation(config, bt)
            requested_and_outcomes.append((True, results.monte_carlo))
        if config.run_regime_analysis:
            results.regime_performance = _run_regime_validation(ticker, config.benchmark, bt, benchmark_df)
            requested_and_outcomes.append((True, results.regime_performance))
        if config.run_cost_stress:
            results.cost_stress = _run_cost_stress_validation(ticker, full_df, start_date, end_date, config)
            requested_and_outcomes.append((True, results.cost_stress))

    experiment.results = results
    experiment.data_provenance = DataProvenance(
        data_source=data_source,
        retrieved_at=_now_iso(),
        data_status=data_status,
        tickers_retrieved=list(price_data.keys()),
        tickers_unavailable=tickers_unavailable,
        latest_market_timestamp=latest_market_timestamp,
    )

    all_requested_succeeded = all(outcome.completed for _, outcome in requested_and_outcomes)
    experiment.status = STATUS_VALIDATED if all_requested_succeeded else STATUS_COMPLETED
    experiment.updated_at = _now_iso()
    store.save_experiment(experiment)
    return experiment


# ------------------------------------------------------- Forward simulation


def start_forward_simulation(experiment_id: str) -> Experiment:
    experiment = store.load_experiment(experiment_id)
    if experiment is None:
        raise ValueError(f"Experiment not found: {experiment_id}")
    if experiment.config.is_portfolio:
        raise ValueError(FORWARD_SIM_UNSUPPORTED_MESSAGE)

    portfolio_id = experiment.id  # already carries the "exp_" prefix from store.new_experiment_id()
    paper_trading_service.reset(portfolio_id, experiment.config.initial_capital)

    experiment.forward_portfolio_id = portfolio_id
    experiment.status = STATUS_PAPER_FORWARD_TEST
    experiment.updated_at = _now_iso()
    store.save_experiment(experiment)
    return experiment


# ---------------------------------------------------------------- Compare


def compare_experiments(experiment_ids: list[str]) -> dict:
    experiments = []
    missing = []
    for exp_id in experiment_ids:
        exp = store.load_experiment(exp_id)
        if exp is None:
            missing.append(exp_id)
        else:
            experiments.append(exp)
    if missing:
        raise ValueError(f"Experiment(s) not found: {', '.join(missing)}")

    warnings: list[str] = []

    spans_years = [
        (dt.date.fromisoformat(e.config.end_date) - dt.date.fromisoformat(e.config.start_date)).days / 365.25
        for e in experiments
    ]
    if spans_years and (max(spans_years) - min(spans_years)) > 0.5:
        warnings.append(
            "Experiments cover periods of different length - direct performance comparison may be misleading."
        )
    if len({e.config.start_date for e in experiments}) > 1 or len({e.config.end_date for e in experiments}) > 1:
        warnings.append(
            "Experiments cover different date ranges - performance differences may reflect different market "
            "conditions rather than a genuine difference between configurations."
        )
    versions = {e.config.model_version for e in experiments}
    if len(versions) > 1:
        warnings.append(f"Experiments use different model versions ({', '.join(sorted(versions))}).")
    universes = {tuple(sorted(e.config.tickers)) for e in experiments}
    if len(universes) > 1:
        warnings.append("Experiments use different ticker universes.")

    return {
        "experiments": experiments,
        "warnings": warnings,
    }


# --------------------------------------------- Forward vs. historical (V5)


def _historical_expectation(experiment: Experiment) -> tuple[dict | None, str | None]:
    """Prefers the out-of-sample OUT_OF_SAMPLE period (held-out data, the
    most honest "historical expectation" available) over the plain backtest
    (which includes the in-sample period the model/thresholds were tuned
    against, if at all) - falls back to the backtest only if OOS wasn't
    requested or didn't complete.
    """
    if experiment.results is None:
        return None, None

    oos = experiment.results.out_of_sample
    if oos.completed and oos.result:
        periods = oos.result.get("periods", [])
        oos_period = next((p for p in periods if p.get("label") == "OUT_OF_SAMPLE"), None)
        if oos_period and oos_period.get("total_return_percent") is not None:
            return {
                "return_percent": oos_period.get("total_return_percent"),
                "sharpe_ratio": oos_period.get("sharpe_ratio"),
                "max_drawdown_percent": oos_period.get("max_drawdown_percent"),
            }, "OUT_OF_SAMPLE"

    bt = experiment.results.backtest
    if bt.completed and bt.result and bt.result.get("total_return_percent") is not None:
        return {
            "return_percent": bt.result.get("total_return_percent"),
            "sharpe_ratio": bt.result.get("sharpe_ratio"),
            "max_drawdown_percent": bt.result.get("max_drawdown_percent"),
        }, "BACKTEST"

    return None, None


def _forward_sharpe(portfolio_id: str) -> float | None:
    history = paper_trading_service.get_equity_history(portfolio_id)
    if len(history.snapshots) < 5:
        return None

    equity = pd.Series([s.equity for s in history.snapshots])
    return backtest_metrics.sharpe_ratio(equity.pct_change())


def get_forward_vs_historical(experiment_id: str) -> dict:
    experiment = store.load_experiment(experiment_id)
    if experiment is None:
        raise ValueError(f"Experiment not found: {experiment_id}")

    if not experiment.forward_portfolio_id:
        return {
            "available": False,
            "reason": "No forward simulation has been started from this experiment yet.",
            "historical": None,
            "historical_source": None,
            "forward": None,
            "forward_sample_developing": True,
            "deviation_notes": [],
        }

    fv = forward_validation.get_forward_validation(experiment.forward_portfolio_id)
    historical, historical_source = _historical_expectation(experiment)

    forward = {
        "return_percent": fv.total_return_percent,
        "sharpe_ratio": _forward_sharpe(experiment.forward_portfolio_id),
        "max_drawdown_percent": fv.max_drawdown_percent,
        "trading_days_observed": fv.trading_days_observed,
    }

    deviation_notes: list[str] = []
    if historical is None:
        deviation_notes.append("No historical backtest or out-of-sample result is available on this experiment to compare against.")
    elif fv.insufficient_sample:
        deviation_notes.append(
            f"Forward sample is still developing ({fv.trading_days_observed} trading day(s) observed) - "
            "too early to compare meaningfully against the historical expectation."
        )
    else:
        if historical.get("return_percent") is not None and forward["return_percent"] is not None:
            diff = forward["return_percent"] - historical["return_percent"]
            if abs(diff) >= FORWARD_DEVIATION_MATERIAL_THRESHOLD_PP:
                direction = "higher" if diff > 0 else "lower"
                deviation_notes.append(
                    f"Forward return is materially {direction} than the historical expectation "
                    f"({forward['return_percent']:.1f}% vs {historical['return_percent']:.1f}%, a "
                    f"{abs(diff):.1f} percentage-point difference)."
                )
            else:
                deviation_notes.append("Forward return is currently within the historical expectation's range.")

        if historical.get("max_drawdown_percent") is not None and forward["max_drawdown_percent"] is not None:
            dd_diff = forward["max_drawdown_percent"] - historical["max_drawdown_percent"]
            if abs(dd_diff) >= FORWARD_DEVIATION_MATERIAL_THRESHOLD_PP:
                direction = "deeper" if dd_diff < 0 else "shallower"
                deviation_notes.append(f"Forward drawdown is materially {direction} than the historical expectation.")

    return {
        "available": True,
        "reason": None,
        "historical": historical,
        "historical_source": historical_source,
        "forward": forward,
        "forward_sample_developing": fv.insufficient_sample,
        "deviation_notes": deviation_notes,
    }
