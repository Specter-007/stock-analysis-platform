from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.experiments import service
from app.experiments.models import Experiment, ExperimentConfig
from app.models.schemas import (
    ArchiveExperimentRequest,
    CompareExperimentsRequest,
    CompareExperimentsResponse,
    CreateExperimentRequest,
    DataProvenanceModel,
    DuplicateExperimentRequest,
    ExperimentConfigModel,
    ExperimentListResponse,
    ExperimentListRowModel,
    ExperimentResponse,
    ExperimentResultsModel,
    ValidationOutcomeModel,
)
from app.services import market_data
from app.utils.validation import normalize_and_validate_ticker

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


def _config_model_to_dataclass(m: ExperimentConfigModel) -> ExperimentConfig:
    return ExperimentConfig(
        model_version=m.model_version,
        tickers=[normalize_and_validate_ticker(t) for t in m.tickers],
        benchmark=normalize_and_validate_ticker(m.benchmark),
        start_date=str(m.start_date),
        end_date=str(m.end_date),
        initial_capital=m.initial_capital,
        commission_bps=m.commission_bps,
        slippage_bps=m.slippage_bps,
        allocation_method=m.allocation_method,
        rebalance_frequency=m.rebalance_frequency,
        portfolio_constraints=m.portfolio_constraints.model_dump() if m.portfolio_constraints else None,
        run_out_of_sample=m.run_out_of_sample,
        run_walk_forward=m.run_walk_forward,
        run_sensitivity=m.run_sensitivity,
        run_monte_carlo=m.run_monte_carlo,
        run_regime_analysis=m.run_regime_analysis,
        run_cost_stress=m.run_cost_stress,
        monte_carlo_simulations=m.monte_carlo_simulations,
        monte_carlo_seed=m.monte_carlo_seed,
        sensitivity_parameters=list(m.sensitivity_parameters),
        walk_forward_train_years=m.walk_forward_train_years,
        walk_forward_test_years=m.walk_forward_test_years,
        walk_forward_max_folds=m.walk_forward_max_folds,
    )


def _experiment_to_response(exp: Experiment) -> ExperimentResponse:
    results_model = None
    if exp.results:
        results_model = ExperimentResultsModel(
            backtest=ValidationOutcomeModel(**asdict(exp.results.backtest)),
            out_of_sample=ValidationOutcomeModel(**asdict(exp.results.out_of_sample)),
            walk_forward=ValidationOutcomeModel(**asdict(exp.results.walk_forward)),
            sensitivity=ValidationOutcomeModel(**asdict(exp.results.sensitivity)),
            monte_carlo=ValidationOutcomeModel(**asdict(exp.results.monte_carlo)),
            regime_performance=ValidationOutcomeModel(**asdict(exp.results.regime_performance)),
            cost_stress=ValidationOutcomeModel(**asdict(exp.results.cost_stress)),
        )
    provenance_model = DataProvenanceModel(**asdict(exp.data_provenance)) if exp.data_provenance else None

    return ExperimentResponse(
        id=exp.id,
        name=exp.name,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
        status=exp.status,
        config=ExperimentConfigModel(**asdict(exp.config)),
        fingerprint=exp.fingerprint,
        notes=exp.notes,
        tags=exp.tags,
        results=results_model,
        data_provenance=provenance_model,
        error=exp.error,
        forward_portfolio_id=exp.forward_portfolio_id,
        reproduced_from=exp.reproduced_from,
        archived=exp.archived,
    )


def _get_or_404(experiment_id: str) -> Experiment:
    exp = service.get_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    return exp


@router.post("", response_model=ExperimentResponse)
def create_experiment(request: CreateExperimentRequest):
    config = _config_model_to_dataclass(request.config)
    exp = service.create_experiment(config, name=request.name, notes=request.notes, tags=request.tags)
    return _experiment_to_response(exp)


@router.get("", response_model=ExperimentListResponse)
def list_experiments(include_archived: bool = Query(default=False)):
    rows = service.list_experiments(include_archived=include_archived)
    return ExperimentListResponse(
        experiments=[
            ExperimentListRowModel(
                experiment=_experiment_to_response(row["experiment"]),
                group_count=row["group_count"],
                data_mining_warning=row["data_mining_warning"],
            )
            for row in rows
        ]
    )


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: str):
    return _experiment_to_response(_get_or_404(experiment_id))


@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: str):
    if not service.delete_experiment(experiment_id):
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    return {"deleted": True, "id": experiment_id}


@router.post("/{experiment_id}/run", response_model=ExperimentResponse)
def run_experiment(experiment_id: str):
    experiment = _get_or_404(experiment_id)
    config = experiment.config

    all_symbols = list(dict.fromkeys(config.tickers + [config.benchmark]))
    with ThreadPoolExecutor(max_workers=min(8, len(all_symbols))) as pool:
        fetch_results = dict(zip(all_symbols, pool.map(_safe_fetch, all_symbols)))

    price_data: dict = {}
    tickers_unavailable: dict[str, str] = {}
    for t in config.tickers:
        df, error = fetch_results[t]
        if df is not None and not df.empty:
            price_data[t] = df
        else:
            tickers_unavailable[t] = error or "No data available."

    if not config.is_portfolio and config.tickers[0] in tickers_unavailable:
        raise HTTPException(
            status_code=422,
            detail=f"'{config.tickers[0]}' data unavailable: {tickers_unavailable[config.tickers[0]]}",
        )

    benchmark_df, benchmark_error = fetch_results.get(config.benchmark, (None, "not fetched"))
    latest_ts = None
    data_status = "HISTORICAL"
    if price_data:
        any_df = next(iter(price_data.values()))
        latest_ts = str(any_df.index[-1])

    ran = service.run_experiment(
        experiment_id=experiment_id,
        price_data=price_data,
        benchmark_df=benchmark_df if benchmark_df is not None and not benchmark_df.empty else None,
        tickers_unavailable=tickers_unavailable,
        data_status=data_status,
        latest_market_timestamp=latest_ts,
    )
    return _experiment_to_response(ran)


def _safe_fetch(ticker: str):
    try:
        df, _meta = market_data.get_full_daily_history(ticker)
        return df, None
    except Exception as exc:
        return None, str(exc)


@router.post("/{experiment_id}/duplicate", response_model=ExperimentResponse)
def duplicate_experiment(experiment_id: str, request: DuplicateExperimentRequest):
    _get_or_404(experiment_id)
    duplicate = service.duplicate_experiment(experiment_id, new_name=request.new_name)
    return _experiment_to_response(duplicate)


@router.post("/{experiment_id}/archive", response_model=ExperimentResponse)
def archive_experiment(experiment_id: str, request: ArchiveExperimentRequest):
    _get_or_404(experiment_id)
    updated = service.archive_experiment(experiment_id, archived=request.archived)
    return _experiment_to_response(updated)


@router.post("/{experiment_id}/forward-simulation", response_model=ExperimentResponse)
def start_forward_simulation(experiment_id: str):
    _get_or_404(experiment_id)
    try:
        updated = service.start_forward_simulation(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _experiment_to_response(updated)


@router.post("/compare", response_model=CompareExperimentsResponse)
def compare_experiments(request: CompareExperimentsRequest):
    try:
        result = service.compare_experiments(request.experiment_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CompareExperimentsResponse(
        experiments=[_experiment_to_response(e) for e in result["experiments"]],
        warnings=result["warnings"],
    )


@router.get("/{experiment_id}/export")
def export_experiment(experiment_id: str):
    experiment = _get_or_404(experiment_id)
    from app.experiments import store as experiments_store

    payload = experiments_store.experiment_to_dict(experiment)
    body = json.dumps(payload, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{experiment_id}.json"'},
    )
