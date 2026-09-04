from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.backtesting.cost_stress import run_cost_stress_test
from app.backtesting.engine import BacktestResult, run_backtest
from app.backtesting.monte_carlo import run_monte_carlo
from app.backtesting.out_of_sample import run_out_of_sample_validation
from app.backtesting.portfolio import (
    ALLOCATION_METHODS,
    REBALANCE_FREQUENCIES,
    PortfolioConstraints,
    run_portfolio_backtest,
)
from app.backtesting.sensitivity import (
    ALL_PARAMETERS,
    THRESHOLD_PARAMETERS,
    run_sensitivity_analysis,
    run_sensitivity_heatmap,
)
from app.backtesting.walk_forward import run_walk_forward
from app.models.schemas import (
    BacktestRequest,
    BacktestResponse,
    CostStressRequest,
    CostStressResponse,
    CostStressScenarioModel,
    MonteCarloRequest,
    MonteCarloResponse,
    OutOfSampleRequest,
    OutOfSampleResponse,
    PeriodResultModel,
    PortfolioBacktestRequest,
    PortfolioBacktestResponse,
    PortfolioEquityPointModel,
    PortfolioHoldingSnapshotModel,
    SensitivityHeatmapCellModel,
    SensitivityHeatmapRequest,
    SensitivityHeatmapResponse,
    SensitivityPointModel,
    SensitivityRequest,
    SensitivityResponse,
    SensitivityResultModel,
    WalkForwardFoldModel,
    WalkForwardRequest,
    WalkForwardResponse,
)
from app.services import market_data
from app.utils.validation import normalize_and_validate_ticker

router = APIRouter(prefix="/api", tags=["backtest"])

BACKTEST_METHODOLOGY = {
    "signal_source": (
        "Every simulated trade decision uses the exact same deterministic scoring "
        "engine as the live Stock Analysis signal - no separate 'backtest-only' strategy."
    ),
    "no_look_ahead": (
        "The signal for day T is computed from indicators using only data through day T's "
        "close. Any resulting position change executes at day T+1's opening price, never "
        "at day T's own close."
    ),
    "position_model": (
        "Long-or-flat only: BUY/STRONG BUY holds a full position in cash-equivalent shares; "
        "HOLD/SELL/STRONG SELL moves fully to cash. Short selling is not modeled."
    ),
    "costs": (
        "Transaction cost and slippage (in basis points) are applied as a price haircut on "
        "every executed entry and exit, in the unfavorable direction."
    ),
    "limitations": (
        "Past performance does not guarantee future results. This backtest does not model "
        "taxes, dividends, borrowing costs, partial fills, or real-world execution latency."
    ),
}


def _resolve_benchmark(ticker: str, benchmark_ticker: str | None):
    if not benchmark_ticker:
        return None, None
    normalized = normalize_and_validate_ticker(benchmark_ticker)
    if normalized == ticker:
        return None, None
    try:
        df, _ = market_data.get_full_daily_history(normalized)
        return normalized, df
    except Exception:
        return None, None


def _to_backtest_response(result: BacktestResult, meta_dict: dict) -> BacktestResponse:
    return BacktestResponse(
        ticker=result.ticker,
        start_date=result.start_date,
        end_date=result.end_date,
        initial_capital=result.initial_capital,
        final_capital=result.final_capital,
        total_return_percent=result.total_return_percent,
        annualized_return_percent=result.annualized_return_percent,
        buy_hold_return_percent=result.buy_hold_return_percent,
        benchmark_ticker=result.benchmark_ticker,
        benchmark_return_percent=result.benchmark_return_percent,
        max_drawdown_percent=result.max_drawdown_percent,
        sharpe_ratio=result.sharpe_ratio,
        trading_days=result.trading_days,
        open_position_at_end=result.open_position_at_end,
        number_of_trades=result.trade_stats.get("number_of_trades", 0),
        winning_trades=result.trade_stats.get("winning_trades", 0),
        losing_trades=result.trade_stats.get("losing_trades", 0),
        win_rate_percent=result.trade_stats.get("win_rate_percent"),
        average_trade_percent=result.trade_stats.get("average_trade_percent"),
        best_trade_percent=result.trade_stats.get("best_trade_percent"),
        worst_trade_percent=result.trade_stats.get("worst_trade_percent"),
        profit_factor=result.trade_stats.get("profit_factor"),
        trades=[t.__dict__ for t in result.trades],
        strategy_curve=[p.__dict__ for p in result.strategy_curve],
        buy_hold_curve=[p.__dict__ for p in result.buy_hold_curve],
        benchmark_curve=[p.__dict__ for p in result.benchmark_curve],
        drawdown_curve=[p.__dict__ for p in result.drawdown_curve],
        warnings=result.warnings,
        methodology=BACKTEST_METHODOLOGY,
        model_version=result.model_version,
        advanced_metrics=result.advanced_metrics,
        meta=meta_dict,
    )


@router.post("/backtest", response_model=BacktestResponse)
def post_backtest(request: BacktestRequest):
    ticker = normalize_and_validate_ticker(request.ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)
    benchmark_ticker, benchmark_df = _resolve_benchmark(ticker, request.benchmark_ticker)

    result = run_backtest(
        ticker=ticker,
        full_price_df=full_df,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        transaction_cost_bps=request.transaction_cost_bps,
        slippage_bps=request.slippage_bps,
        benchmark_ticker=benchmark_ticker,
        benchmark_full_price_df=benchmark_df,
        model_version=request.model_version,
    )

    return _to_backtest_response(result, meta.to_dict())


@router.post("/backtest/walk-forward", response_model=WalkForwardResponse)
def post_walk_forward(request: WalkForwardRequest):
    ticker = normalize_and_validate_ticker(request.ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)

    result = run_walk_forward(
        ticker=ticker,
        full_price_df=full_df,
        train_years=request.train_years,
        test_years=request.test_years,
        max_folds=request.max_folds,
        initial_capital=request.initial_capital,
        transaction_cost_bps=request.transaction_cost_bps,
        slippage_bps=request.slippage_bps,
    )

    return WalkForwardResponse(
        ticker=result.ticker,
        train_years=result.train_years,
        test_years=result.test_years,
        folds=[WalkForwardFoldModel(**f.__dict__) for f in result.folds],
        folds_with_positive_return=result.folds_with_positive_return,
        average_test_return_percent=result.average_test_return_percent,
        methodology=result.methodology,
        meta=meta.to_dict(),
    )


@router.post("/backtest/monte-carlo", response_model=MonteCarloResponse)
def post_monte_carlo(request: MonteCarloRequest):
    ticker = normalize_and_validate_ticker(request.ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)

    backtest_result = run_backtest(
        ticker=ticker,
        full_price_df=full_df,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        transaction_cost_bps=request.transaction_cost_bps,
        slippage_bps=request.slippage_bps,
    )

    equity_series = pd.Series(
        {p.date: p.equity for p in backtest_result.strategy_curve}
    )
    daily_returns = equity_series.pct_change()

    mc_result = run_monte_carlo(
        trades=backtest_result.trades,
        daily_returns=daily_returns,
        initial_capital=request.initial_capital,
        num_simulations=request.simulations,
        seed=request.seed,
        drawdown_threshold_percent=request.drawdown_threshold_percent,
        trading_days_in_period=backtest_result.trading_days,
    )

    return MonteCarloResponse(
        ticker=ticker,
        simulations=mc_result.simulations,
        resampling_basis=mc_result.resampling_basis,
        resampling_method=mc_result.resampling_method,
        sample_size=mc_result.sample_size,
        seed=mc_result.seed,
        median_return_percent=mc_result.median_return_percent,
        percentile_5_return_percent=mc_result.percentile_5_return_percent,
        percentile_95_return_percent=mc_result.percentile_95_return_percent,
        median_max_drawdown_percent=mc_result.median_max_drawdown_percent,
        worst_max_drawdown_percent=mc_result.worst_max_drawdown_percent,
        median_cagr_percent=mc_result.median_cagr_percent,
        percentile_5_cagr_percent=mc_result.percentile_5_cagr_percent,
        percentile_95_cagr_percent=mc_result.percentile_95_cagr_percent,
        median_final_equity=mc_result.median_final_equity,
        percentile_5_final_equity=mc_result.percentile_5_final_equity,
        percentile_95_final_equity=mc_result.percentile_95_final_equity,
        probability_of_loss_percent=mc_result.probability_of_loss_percent,
        drawdown_threshold_percent=mc_result.drawdown_threshold_percent,
        probability_of_exceeding_drawdown_threshold_percent=mc_result.probability_of_exceeding_drawdown_threshold_percent,
        methodology=mc_result.methodology,
        meta=meta.to_dict(),
    )


@router.post("/backtest/cost-stress", response_model=CostStressResponse)
def post_cost_stress(request: CostStressRequest):
    ticker = normalize_and_validate_ticker(request.ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)

    result = run_cost_stress_test(
        ticker=ticker,
        full_price_df=full_df,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        base_commission_bps=request.base_commission_bps,
        base_slippage_bps=request.base_slippage_bps,
        model_version=request.model_version,
    )

    return CostStressResponse(
        ticker=result.ticker,
        gross_return_percent=result.gross_return_percent,
        commission_scenarios=[CostStressScenarioModel(**s.__dict__) for s in result.commission_scenarios],
        slippage_scenarios=[CostStressScenarioModel(**s.__dict__) for s in result.slippage_scenarios],
        methodology=result.methodology,
        meta=meta.to_dict(),
    )


@router.post("/backtest/sensitivity", response_model=SensitivityResponse)
def post_sensitivity(request: SensitivityRequest):
    ticker = normalize_and_validate_ticker(request.ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)

    if request.parameters:
        requested = tuple(p for p in request.parameters if p in ALL_PARAMETERS)
        parameters = requested or THRESHOLD_PARAMETERS
    else:
        parameters = THRESHOLD_PARAMETERS

    result = run_sensitivity_analysis(
        ticker=ticker,
        full_price_df=full_df,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        transaction_cost_bps=request.transaction_cost_bps,
        slippage_bps=request.slippage_bps,
        model_version=request.model_version,
        parameters=parameters,
    )

    return SensitivityResponse(
        ticker=result.ticker,
        model_version=result.model_version,
        parameters=[
            SensitivityResultModel(
                parameter=p.parameter,
                label=p.label,
                default_value=p.default_value,
                points=[SensitivityPointModel(**pt.__dict__) for pt in p.points],
                robustness=p.robustness,
                robust_region_min=p.robust_region_min,
                robust_region_max=p.robust_region_max,
                best_value=p.best_value,
                median_value=p.median_value,
                worst_value=p.worst_value,
                note=p.note,
            )
            for p in result.parameters
        ],
        methodology=result.methodology,
        meta=meta.to_dict(),
    )


@router.post("/backtest/sensitivity/heatmap", response_model=SensitivityHeatmapResponse)
def post_sensitivity_heatmap(request: SensitivityHeatmapRequest):
    ticker = normalize_and_validate_ticker(request.ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)

    if request.param_x not in ALL_PARAMETERS or request.param_y not in ALL_PARAMETERS:
        raise HTTPException(
            status_code=422,
            detail=f"param_x and param_y must both be one of: {', '.join(ALL_PARAMETERS)}",
        )

    result = run_sensitivity_heatmap(
        ticker=ticker,
        full_price_df=full_df,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        transaction_cost_bps=request.transaction_cost_bps,
        slippage_bps=request.slippage_bps,
        param_x=request.param_x,
        param_y=request.param_y,
        metric=request.metric,
        model_version=request.model_version,
    )

    return SensitivityHeatmapResponse(
        ticker=result.ticker,
        param_x=result.param_x,
        param_y=result.param_y,
        metric=result.metric,
        cells=[SensitivityHeatmapCellModel(**c.__dict__) for c in result.cells],
        methodology=result.methodology,
        meta=meta.to_dict(),
    )


@router.post("/backtest/out-of-sample", response_model=OutOfSampleResponse)
def post_out_of_sample(request: OutOfSampleRequest):
    ticker = normalize_and_validate_ticker(request.ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)

    windows = [
        ("IN_SAMPLE", request.in_sample_start, request.in_sample_end),
        ("VALIDATION", request.validation_start, request.validation_end),
        ("OUT_OF_SAMPLE", request.out_of_sample_start, request.out_of_sample_end),
    ]

    result = run_out_of_sample_validation(
        ticker=ticker,
        full_price_df=full_df,
        windows=windows,
        initial_capital=request.initial_capital,
        transaction_cost_bps=request.transaction_cost_bps,
        slippage_bps=request.slippage_bps,
        model_version=request.model_version,
    )

    return OutOfSampleResponse(
        ticker=result.ticker,
        model_version=result.model_version,
        periods=[PeriodResultModel(**p.__dict__) for p in result.periods],
        meta=meta.to_dict(),
    )


@router.post("/backtest/portfolio", response_model=PortfolioBacktestResponse)
def post_portfolio_backtest(request: PortfolioBacktestRequest):
    tickers = [normalize_and_validate_ticker(t) for t in request.tickers]
    if len(set(tickers)) != len(tickers):
        raise HTTPException(status_code=422, detail="Duplicate tickers are not allowed.")
    if request.allocation_method not in ALLOCATION_METHODS:
        raise HTTPException(status_code=422, detail=f"allocation_method must be one of: {', '.join(ALLOCATION_METHODS)}")
    if request.rebalance_frequency not in REBALANCE_FREQUENCIES:
        raise HTTPException(status_code=422, detail=f"rebalance_frequency must be one of: {', '.join(REBALANCE_FREQUENCIES)}")

    with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as pool:
        fetch_results = list(pool.map(market_data.get_full_daily_history, tickers))
    price_data = {t: df for t, (df, _meta) in zip(tickers, fetch_results)}
    meta = fetch_results[0][1]

    benchmark_df = None
    if request.benchmark_ticker:
        try:
            benchmark_df, _ = market_data.get_full_daily_history(request.benchmark_ticker)
        except Exception:
            benchmark_df = None

    constraints = PortfolioConstraints(**request.constraints.model_dump())

    result = run_portfolio_backtest(
        tickers=tickers,
        price_data=price_data,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        transaction_cost_bps=request.transaction_cost_bps,
        slippage_bps=request.slippage_bps,
        allocation_method=request.allocation_method,
        rebalance_frequency=request.rebalance_frequency,
        constraints=constraints,
        fixed_weights=request.fixed_weights,
        model_version=request.model_version,
        benchmark_ticker=request.benchmark_ticker,
        benchmark_price_df=benchmark_df,
    )

    return PortfolioBacktestResponse(
        tickers=result.tickers,
        start_date=result.start_date,
        end_date=result.end_date,
        initial_capital=result.initial_capital,
        final_capital=result.final_capital,
        allocation_method=result.allocation_method,
        rebalance_frequency=result.rebalance_frequency,
        total_return_percent=result.total_return_percent,
        equal_weight_buy_hold_return_percent=result.equal_weight_buy_hold_return_percent,
        benchmark_ticker=result.benchmark_ticker,
        benchmark_return_percent=result.benchmark_return_percent,
        max_drawdown_percent=result.max_drawdown_percent,
        sharpe_ratio=result.sharpe_ratio,
        trading_days=result.trading_days,
        number_of_rebalances=result.number_of_rebalances,
        equity_curve=[PortfolioEquityPointModel(**p.__dict__) for p in result.equity_curve],
        equal_weight_buy_hold_curve=[PortfolioEquityPointModel(**p.__dict__) for p in result.equal_weight_buy_hold_curve],
        benchmark_curve=[PortfolioEquityPointModel(**p.__dict__) for p in result.benchmark_curve],
        drawdown_curve=[PortfolioEquityPointModel(**p.__dict__) for p in result.drawdown_curve],
        holdings_history=[PortfolioHoldingSnapshotModel(**h.__dict__) for h in result.holdings_history],
        advanced_metrics=result.advanced_metrics,
        risk_analytics=result.risk_analytics,
        warnings=result.warnings,
        excluded_tickers=result.excluded_tickers,
        methodology=result.methodology,
        meta=meta.to_dict(),
    )
