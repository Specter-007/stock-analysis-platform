from __future__ import annotations

import pandas as pd
from fastapi import APIRouter

from app.backtesting.engine import BacktestResult, run_backtest
from app.backtesting.monte_carlo import run_monte_carlo
from app.backtesting.out_of_sample import run_out_of_sample_validation
from app.backtesting.sensitivity import run_sensitivity_analysis
from app.backtesting.walk_forward import run_walk_forward
from app.models.schemas import (
    BacktestRequest,
    BacktestResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    OutOfSampleRequest,
    OutOfSampleResponse,
    PeriodResultModel,
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
    )

    return MonteCarloResponse(
        ticker=ticker,
        simulations=mc_result.simulations,
        resampling_basis=mc_result.resampling_basis,
        sample_size=mc_result.sample_size,
        median_return_percent=mc_result.median_return_percent,
        percentile_5_return_percent=mc_result.percentile_5_return_percent,
        percentile_95_return_percent=mc_result.percentile_95_return_percent,
        median_max_drawdown_percent=mc_result.median_max_drawdown_percent,
        worst_max_drawdown_percent=mc_result.worst_max_drawdown_percent,
        methodology=mc_result.methodology,
        meta=meta.to_dict(),
    )


@router.post("/backtest/sensitivity", response_model=SensitivityResponse)
def post_sensitivity(request: SensitivityRequest):
    ticker = normalize_and_validate_ticker(request.ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)

    result = run_sensitivity_analysis(
        ticker=ticker,
        full_price_df=full_df,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        transaction_cost_bps=request.transaction_cost_bps,
        slippage_bps=request.slippage_bps,
        model_version=request.model_version,
    )

    return SensitivityResponse(
        ticker=result.ticker,
        model_version=result.model_version,
        parameters=[
            SensitivityResultModel(
                parameter=p.parameter,
                default_value=p.default_value,
                points=[SensitivityPointModel(**pt.__dict__) for pt in p.points],
                robustness=p.robustness,
                robust_region_min=p.robust_region_min,
                robust_region_max=p.robust_region_max,
                note=p.note,
            )
            for p in result.parameters
        ],
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
