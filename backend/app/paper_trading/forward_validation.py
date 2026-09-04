"""V4 Forward Validation engine.

This answers a conceptually DIFFERENT question from historical backtesting
or out-of-sample validation (`app.backtesting.out_of_sample`):

    Backtest / OOS  -> "How would this model have behaved on past data?"
    Forward validation -> "How does this model actually behave as REAL,
                            live market data arrives from now on?"

It is built entirely on top of the existing paper-trading service (real
signals, real quotes, real commission/slippage, real append-only equity
snapshots) - it never re-implements portfolio bookkeeping, and it never
simulates or fabricates a data point. If the portfolio has not been queried
on enough real trading days yet, that is reported honestly as an
insufficient-sample condition, not papered over with an invented number.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import MODEL_VERSION_CURRENT
from app.paper_trading import service as paper_trading_service

MIN_TRADING_DAYS_FOR_CONFIDENT_METRICS = 20


@dataclass
class ForwardValidationView:
    portfolio_id: str
    model_version: str
    model_version_is_mixed: bool
    start_date: str | None
    current_date: str | None
    trading_days_observed: int
    initial_capital: float
    current_equity: float
    total_return_percent: float
    benchmark_ticker: str | None
    benchmark_return_percent: float | None
    max_drawdown_percent: float | None
    number_of_trades: int  # count of individual BUY/SELL executions, not round trips
    open_positions_count: int
    realized_pnl: float
    unrealized_pnl: float
    insufficient_sample: bool
    warnings: list[str]
    methodology: str = (
        "This is a FORWARD paper-trading observation record, not a backtest. Every data point was "
        "captured as real market data actually arrived - none of it is simulated or replayed "
        "history. max_drawdown_percent is computed from this portfolio's own recorded daily equity "
        "snapshots (peak-to-trough), the same definition used in backtesting, but over live "
        "forward observations instead of historical ones. Metrics from fewer than "
        f"{MIN_TRADING_DAYS_FOR_CONFIDENT_METRICS} observed trading days are flagged "
        "insufficient_sample=true - a return or drawdown figure from a handful of days is not "
        "statistically meaningful and should not be read as validating or invalidating the model."
    )


def _model_version_used(trades) -> tuple[str, bool]:
    versions = {t.model_version for t in trades if t.model_version}
    if not versions:
        return MODEL_VERSION_CURRENT, False
    if len(versions) == 1:
        return next(iter(versions)), False
    return "MIXED", True


def _max_drawdown_percent(equities: list[float]) -> float | None:
    if len(equities) < 2:
        return None
    peak = equities[0]
    worst_dd = 0.0
    for e in equities:
        peak = max(peak, e)
        if peak > 0:
            worst_dd = min(worst_dd, (e - peak) / peak * 100.0)
    return round(worst_dd, 2)


def get_forward_validation(db: Session, user_id: str, portfolio_id: str) -> ForwardValidationView:
    view = paper_trading_service.get_portfolio(db, user_id, portfolio_id)
    history = paper_trading_service.get_equity_history(db, user_id, portfolio_id)

    snapshots = history.snapshots
    trading_days_observed = len(snapshots)
    model_version, is_mixed = _model_version_used(view.trades)

    warnings: list[str] = []

    start_date = snapshots[0].date if snapshots else None
    current_date = snapshots[-1].date if snapshots else None

    benchmark_return_percent = None
    if snapshots and snapshots[0].benchmark_value and snapshots[-1].benchmark_value is not None:
        benchmark_return_percent = round(
            (snapshots[-1].benchmark_value / snapshots[0].benchmark_value - 1.0) * 100.0, 2
        )
    elif not any(s.benchmark_value is not None for s in snapshots):
        if snapshots:
            warnings.append("Benchmark (SPY) data was unavailable, so benchmark_return_percent is N/A.")

    max_dd = _max_drawdown_percent([s.equity for s in snapshots])

    insufficient_sample = trading_days_observed < MIN_TRADING_DAYS_FOR_CONFIDENT_METRICS
    if insufficient_sample:
        warnings.append(
            f"Only {trading_days_observed} trading day(s) of forward observation recorded so far "
            f"(< {MIN_TRADING_DAYS_FOR_CONFIDENT_METRICS}). Return/drawdown figures are not yet "
            "statistically meaningful."
        )
    if is_mixed:
        warnings.append(
            "This portfolio's trades span more than one model version - reported metrics mix "
            "decisions made under different model versions."
        )

    return ForwardValidationView(
        portfolio_id=portfolio_id,
        model_version=model_version,
        model_version_is_mixed=is_mixed,
        start_date=start_date,
        current_date=current_date,
        trading_days_observed=trading_days_observed,
        initial_capital=view.starting_capital,
        current_equity=view.current_value,
        total_return_percent=view.total_return_percent,
        benchmark_ticker=history.benchmark_ticker,
        benchmark_return_percent=benchmark_return_percent,
        max_drawdown_percent=max_dd,
        number_of_trades=len(view.trades),
        open_positions_count=view.number_of_positions,
        realized_pnl=view.realized_pnl,
        unrealized_pnl=view.unrealized_pnl,
        insufficient_sample=insufficient_sample,
        warnings=warnings,
    )
