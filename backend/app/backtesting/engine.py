"""Long/flat backtesting engine driven by the exact same deterministic
signal engine used for live analysis (`app.signals.engine.evaluate`).

No-look-ahead-bias contract
----------------------------
1. The signal for trading day T is computed from `indicator_df` truncated
   to rows with date <= T. Because every indicator in
   `app.indicators.compute` is a causal rolling/EWM computation, the value
   at row T never depends on rows after T - so this truncation doesn't
   change any number, it only documents/enforces the guarantee.
2. A signal computed at day T's close can only change the position
   starting at day T+1's OPEN ("next-bar execution"). It is never applied
   to day T's own close.
3. Transaction cost and slippage are charged on every executed entry/exit,
   applied as a price haircut in the unfavorable direction.

Strategy shape: long-or-flat only. BUY/STRONG_BUY -> hold a full position;
HOLD/SELL/STRONG_SELL -> flat (cash). No shorting is modeled.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.backtesting import metrics as m
from app.backtesting.metrics import Trade
from app.config import MODEL_VERSION_CURRENT
from app.indicators.compute import compute_indicator_frame
from app.services.exceptions import InsufficientHistoryError
from app.signals import engine as signal_engine

MIN_SIM_TRADING_DAYS = 30


@dataclass
class EquityPoint:
    date: str
    equity: float


@dataclass
class BacktestResult:
    ticker: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_percent: float | None
    annualized_return_percent: float | None
    buy_hold_return_percent: float | None
    benchmark_ticker: str | None
    benchmark_return_percent: float | None
    max_drawdown_percent: float | None
    sharpe_ratio: float | None
    trading_days: int
    open_position_at_end: bool
    model_version: str = "1.1"
    trades: list[Trade] = field(default_factory=list)
    strategy_curve: list[EquityPoint] = field(default_factory=list)
    buy_hold_curve: list[EquityPoint] = field(default_factory=list)
    benchmark_curve: list[EquityPoint] = field(default_factory=list)
    drawdown_curve: list[EquityPoint] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trade_stats: dict = field(default_factory=dict)
    advanced_metrics: dict = field(default_factory=dict)


def _build_buy_hold_curve(price_slice: pd.DataFrame, initial_capital: float, cost_rate: float) -> pd.Series:
    entry_price = float(price_slice.iloc[0]["Open"]) * (1 + cost_rate)
    shares = initial_capital / entry_price if entry_price > 0 else 0.0
    return shares * price_slice["Close"]


def run_backtest(
    ticker: str,
    full_price_df: pd.DataFrame,
    start_date: dt.date,
    end_date: dt.date,
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
    benchmark_ticker: str | None = None,
    benchmark_full_price_df: pd.DataFrame | None = None,
    model_version: str = MODEL_VERSION_CURRENT,
    thresholds: signal_engine.ScoreThresholds = signal_engine.DEFAULT_THRESHOLDS,
    precomputed_indicator_df: pd.DataFrame | None = None,
) -> BacktestResult:
    # `precomputed_indicator_df` lets parameter-sensitivity analysis substitute
    # indicator columns computed with non-default periods (see
    # backtesting/parametrized_indicators.py) without this function - or the
    # standard v1.0/v1.1 code path - ever needing to know about it.
    indicator_df = precomputed_indicator_df if precomputed_indicator_df is not None else compute_indicator_frame(full_price_df)
    idx_dates = indicator_df.index

    sim_mask = (idx_dates.date >= start_date) & (idx_dates.date <= end_date)
    sim_dates = idx_dates[sim_mask]

    if len(sim_dates) < MIN_SIM_TRADING_DAYS:
        raise InsufficientHistoryError(ticker, len(sim_dates), MIN_SIM_TRADING_DAYS)

    cost_rate = (transaction_cost_bps + slippage_bps) / 10_000.0

    cash = initial_capital
    shares = 0.0
    in_position = False
    open_trade: Trade | None = None
    trades: list[Trade] = []
    equity_points: list[tuple[pd.Timestamp, float]] = []
    pending_action: str | None = None
    warnings: list[str] = []

    dates_list = list(sim_dates)

    first_row = indicator_df.loc[dates_list[0]]
    if pd.isna(first_row.get("SMA_200")):
        warnings.append(
            "Insufficient warmup history for the 200-day SMA at the start of the "
            "requested period; early signals in this backtest used fewer trend factors."
        )

    for date in dates_list:
        row = indicator_df.loc[date]
        today_open = float(row["Open"])
        today_close = float(row["Close"])

        if pending_action == "ENTER" and not in_position:
            effective_price = today_open * (1 + cost_rate)
            if effective_price > 0:
                shares = cash / effective_price
                cash = 0.0
                in_position = True
                open_trade = Trade(
                    entry_date=str(date.date()),
                    entry_price=effective_price,
                    exit_date=None,
                    exit_price=None,
                    shares=shares,
                    pnl=None,
                    pnl_pct=None,
                )
        elif pending_action == "EXIT" and in_position and open_trade is not None:
            effective_price = today_open * (1 - cost_rate)
            proceeds = shares * effective_price
            entry_cost_basis = open_trade.entry_price * open_trade.shares
            open_trade.exit_date = str(date.date())
            open_trade.exit_price = effective_price
            open_trade.pnl = proceeds - entry_cost_basis
            open_trade.pnl_pct = (
                (effective_price / open_trade.entry_price - 1.0) * 100.0
                if open_trade.entry_price
                else None
            )
            trades.append(open_trade)
            open_trade = None
            cash = proceeds
            shares = 0.0
            in_position = False

        pending_action = None

        equity = cash + shares * today_close
        equity_points.append((date, equity))

        historical_slice = indicator_df.loc[:date]
        try:
            sig = signal_engine.evaluate(historical_slice, model_version=model_version, thresholds=thresholds)
            desired_long = sig.signal in ("BUY", "STRONG_BUY")
        except Exception:
            desired_long = in_position

        if desired_long and not in_position:
            pending_action = "ENTER"
        elif not desired_long and in_position:
            pending_action = "EXIT"

    open_position_at_end = in_position
    if open_position_at_end:
        warnings.append(
            "A position was still open at the end of the requested period. Final "
            "capital reflects mark-to-market value, not an executed sale."
        )

    equity_series = pd.Series(
        [e for _, e in equity_points], index=[d for d, _ in equity_points], name="equity"
    )
    daily_returns = equity_series.pct_change()

    final_capital = float(equity_series.iloc[-1])
    trading_days = len(equity_series)

    price_slice = full_price_df.loc[full_price_df.index.isin(sim_dates)]
    buy_hold_series = _build_buy_hold_curve(price_slice, initial_capital, cost_rate)
    buy_hold_return = m.total_return(initial_capital, float(buy_hold_series.iloc[-1]))

    benchmark_return = None
    benchmark_curve_points: list[EquityPoint] = []
    if benchmark_ticker and benchmark_full_price_df is not None and not benchmark_full_price_df.empty:
        bench_mask = (
            benchmark_full_price_df.index.date >= start_date
        ) & (benchmark_full_price_df.index.date <= end_date)
        bench_slice = benchmark_full_price_df.loc[bench_mask]
        if not bench_slice.empty:
            bench_series = _build_buy_hold_curve(bench_slice, initial_capital, cost_rate)
            benchmark_return = m.total_return(initial_capital, float(bench_series.iloc[-1]))
            benchmark_curve_points = [
                EquityPoint(date=str(d.date()), equity=round(float(v), 2))
                for d, v in bench_series.items()
            ]
        else:
            warnings.append(f"No benchmark data available for '{benchmark_ticker}' in the requested range.")

    drawdown_series = (equity_series - equity_series.cummax()) / equity_series.cummax() * 100.0

    stats = m.trade_stats(trades)

    cagr_pct = m.cagr(initial_capital, final_capital, trading_days)
    max_dd_pct = m.max_drawdown_percent(equity_series)

    advanced_metrics: dict = {
        "cagr_percent": round(cagr_pct, 2) if cagr_pct is not None else None,
        "annualized_volatility_percent": m.annualized_volatility_percent(daily_returns),
        "sortino_ratio": (round(v, 3) if (v := m.sortino_ratio(daily_returns)) is not None else None),
        "calmar_ratio": m.calmar_ratio(cagr_pct, max_dd_pct),
        "average_drawdown_percent": m.average_drawdown_percent(equity_series),
        "downside_deviation_percent": m.downside_deviation_percent(daily_returns),
        "max_drawdown_recovery_days": m.max_drawdown_recovery_days(equity_series),
        "expectancy": m.expectancy(trades),
        "exposure_percent": m.exposure_percent(trades, trading_days),
        "turnover_percent": m.turnover_percent(trades, initial_capital),
        "beta": None,
        "alpha_percent": None,
        "tracking_error_percent": None,
        "information_ratio": None,
    }
    advanced_metrics.update(m.average_win_loss(trades))

    if benchmark_ticker and benchmark_curve_points:
        # Both sides are reindexed onto plain python `date` objects before
        # aligning: `equity_series.index` is timezone-aware (from yfinance),
        # while `benchmark_curve_points[i].date` is a naive "YYYY-MM-DD"
        # string - reindexing a naive-keyed Series against a tz-aware index
        # silently matches nothing (not an error, just all-NaN), which
        # previously made beta/alpha/tracking-error/information-ratio None
        # even when a valid benchmark was supplied. See regression test
        # `test_beta_alpha_present_with_tz_aware_equity_index`.
        strategy_by_date = {ts.date(): v for ts, v in equity_series.items()}
        bench_by_date = {pd.Timestamp(p.date).date(): p.equity for p in benchmark_curve_points}
        common_dates = sorted(set(strategy_by_date) & set(bench_by_date))
        strategy_equity_aligned = pd.Series([strategy_by_date[d] for d in common_dates], index=common_dates)
        bench_equity_aligned = pd.Series([bench_by_date[d] for d in common_dates], index=common_dates)
        strategy_returns_aligned = strategy_equity_aligned.pct_change()
        bench_returns_aligned = bench_equity_aligned.pct_change()
        beta_alpha = m.beta_alpha_tracking_error(strategy_returns_aligned, bench_returns_aligned)
        advanced_metrics.update(beta_alpha)

    return BacktestResult(
        ticker=ticker,
        start_date=str(start_date),
        end_date=str(end_date),
        initial_capital=round(initial_capital, 2),
        final_capital=round(final_capital, 2),
        total_return_percent=round(m.total_return(initial_capital, final_capital), 2)
        if m.total_return(initial_capital, final_capital) is not None
        else None,
        annualized_return_percent=(
            round(v, 2) if (v := m.annualized_return(initial_capital, final_capital, trading_days)) is not None else None
        ),
        buy_hold_return_percent=round(buy_hold_return, 2) if buy_hold_return is not None else None,
        benchmark_ticker=benchmark_ticker,
        benchmark_return_percent=round(benchmark_return, 2) if benchmark_return is not None else None,
        max_drawdown_percent=m.max_drawdown_percent(equity_series),
        sharpe_ratio=(round(sr, 3) if (sr := m.sharpe_ratio(daily_returns)) is not None else None),
        trading_days=trading_days,
        open_position_at_end=open_position_at_end,
        model_version=model_version,
        trades=trades,
        strategy_curve=[EquityPoint(date=str(d.date()), equity=round(v, 2)) for d, v in equity_series.items()],
        buy_hold_curve=[EquityPoint(date=str(d.date()), equity=round(float(v), 2)) for d, v in buy_hold_series.items()],
        benchmark_curve=benchmark_curve_points,
        drawdown_curve=[EquityPoint(date=str(d.date()), equity=round(float(v), 2)) for d, v in drawdown_series.items()],
        warnings=warnings,
        trade_stats=stats,
        advanced_metrics=advanced_metrics,
    )
