from __future__ import annotations

from fastapi import APIRouter

from app.backtesting.engine import run_backtest
from app.models.schemas import BacktestRequest, BacktestResponse
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


@router.post("/backtest", response_model=BacktestResponse)
def post_backtest(request: BacktestRequest):
    ticker = normalize_and_validate_ticker(request.ticker)

    full_df, meta = market_data.get_full_daily_history(ticker)

    benchmark_ticker = None
    benchmark_df = None
    if request.benchmark_ticker:
        benchmark_ticker = normalize_and_validate_ticker(request.benchmark_ticker)
        if benchmark_ticker == ticker:
            benchmark_ticker = None
        else:
            try:
                benchmark_df, _ = market_data.get_full_daily_history(benchmark_ticker)
            except Exception:
                benchmark_df = None

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
    )

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
        meta=meta.to_dict(),
    )
