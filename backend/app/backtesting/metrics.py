"""Pure metric calculations over an equity curve / trade list. No I/O, no
randomness - each function takes plain pandas/python data structures so it
can be unit tested with synthetic fixtures independent of yfinance.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.config import HIST_VOL_ANNUALIZATION, RISK_FREE_RATE_ANNUAL
from app.utils.finance import max_drawdown


@dataclass
class Trade:
    entry_date: str
    entry_price: float
    exit_date: str | None
    exit_price: float | None
    shares: float
    pnl: float | None
    pnl_pct: float | None


def total_return(initial_capital: float, final_capital: float) -> float | None:
    if initial_capital <= 0:
        return None
    return (final_capital / initial_capital - 1.0) * 100.0


def annualized_return(initial_capital: float, final_capital: float, trading_days: int) -> float | None:
    if initial_capital <= 0 or trading_days <= 0:
        return None
    growth = final_capital / initial_capital
    if growth <= 0:
        return None
    years = trading_days / HIST_VOL_ANNUALIZATION
    if years <= 0:
        return None
    return (growth ** (1.0 / years) - 1.0) * 100.0


def sharpe_ratio(daily_returns: pd.Series) -> float | None:
    """Annualized Sharpe ratio from a series of daily fractional returns.
    Returns None (N/A) when there isn't enough variance to compute one
    meaningfully, rather than fabricating a number.
    """
    clean = daily_returns.dropna()
    if len(clean) < 2:
        return None
    std = clean.std(ddof=0)
    if std == 0 or np.isnan(std):
        return None
    daily_rf = RISK_FREE_RATE_ANNUAL / HIST_VOL_ANNUALIZATION
    mean_excess = clean.mean() - daily_rf
    return float((mean_excess / std) * np.sqrt(HIST_VOL_ANNUALIZATION))


def trade_stats(trades: list[Trade]) -> dict:
    closed = [t for t in trades if t.pnl is not None]
    if not closed:
        return {
            "number_of_trades": len(trades),
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate_percent": None,
            "average_trade_percent": None,
            "best_trade_percent": None,
            "worst_trade_percent": None,
            "profit_factor": None,
        }

    pnls_pct = [t.pnl_pct for t in closed if t.pnl_pct is not None]
    wins = [t for t in closed if t.pnl > 0]
    losses = [t for t in closed if t.pnl < 0]

    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))

    profit_factor = None
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = None  # undefined (no losing trades) - reported as N/A, not infinity

    return {
        "number_of_trades": len(closed),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate_percent": round(len(wins) / len(closed) * 100, 2) if closed else None,
        "average_trade_percent": round(float(np.mean(pnls_pct)), 2) if pnls_pct else None,
        "best_trade_percent": round(float(np.max(pnls_pct)), 2) if pnls_pct else None,
        "worst_trade_percent": round(float(np.min(pnls_pct)), 2) if pnls_pct else None,
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
    }


def max_drawdown_percent(equity: pd.Series) -> float | None:
    dd = max_drawdown(equity)
    return round(dd * 100, 2) if dd is not None else None


def cagr(initial_capital: float, final_capital: float, trading_days: int) -> float | None:
    """Compound Annual Growth Rate - identical formula to `annualized_return`,
    exposed under its conventional name for the Model Evaluation surfaces."""
    return annualized_return(initial_capital, final_capital, trading_days)


def annualized_volatility_percent(daily_returns: pd.Series) -> float | None:
    clean = daily_returns.dropna()
    if len(clean) < 2:
        return None
    std = clean.std(ddof=0)
    if np.isnan(std):
        return None
    return round(float(std * np.sqrt(HIST_VOL_ANNUALIZATION) * 100.0), 2)


def sortino_ratio(daily_returns: pd.Series) -> float | None:
    """Like Sharpe, but the denominator is downside deviation (std of only
    negative excess returns) rather than total volatility - a strategy with
    large upside swings and no downside is not penalized.
    """
    clean = daily_returns.dropna()
    if len(clean) < 2:
        return None
    daily_rf = RISK_FREE_RATE_ANNUAL / HIST_VOL_ANNUALIZATION
    excess = clean - daily_rf
    downside = excess[excess < 0]
    if len(downside) == 0:
        return None
    downside_std = np.sqrt((downside ** 2).mean())
    if downside_std == 0 or np.isnan(downside_std):
        return None
    return float((excess.mean() / downside_std) * np.sqrt(HIST_VOL_ANNUALIZATION))


def downside_deviation_percent(daily_returns: pd.Series) -> float | None:
    clean = daily_returns.dropna()
    if len(clean) < 2:
        return None
    negative = clean[clean < 0]
    if len(negative) == 0:
        return 0.0
    return round(float(np.sqrt((negative ** 2).mean()) * np.sqrt(HIST_VOL_ANNUALIZATION) * 100.0), 2)


def calmar_ratio(cagr_percent: float | None, max_dd_percent: float | None) -> float | None:
    """CAGR / |max drawdown|. Undefined (None) when there's no drawdown to
    divide by, or no CAGR to compare - never silently reported as infinity.
    """
    if cagr_percent is None or max_dd_percent is None or max_dd_percent == 0:
        return None
    return round(cagr_percent / abs(max_dd_percent), 2)


def average_drawdown_percent(equity: pd.Series) -> float | None:
    """Mean depth of every distinct drawdown episode (trough vs. its prior
    peak), not just the single worst one - a fuller picture of typical pain.
    """
    from app.utils.finance import running_max_drawdown_series

    if equity is None or len(equity) < 2:
        return None
    dd_series = running_max_drawdown_series(equity)
    in_drawdown = dd_series[dd_series < 0]
    if in_drawdown.empty:
        return 0.0
    return round(float(in_drawdown.mean()) * 100.0, 2)


def max_drawdown_recovery_days(equity: pd.Series) -> int | None:
    """Trading days from the equity curve's worst trough back to a new
    all-time high. None if the curve never recovers within the sample
    (still underwater at the end) - reported as N/A, not a fabricated number.
    """
    if equity is None or len(equity) < 2:
        return None
    running_peak = equity.cummax()
    dd = (equity - running_peak) / running_peak
    trough_idx = dd.idxmin()
    trough_pos = equity.index.get_loc(trough_idx)
    peak_at_trough = running_peak.loc[trough_idx]

    after_trough = equity.iloc[trough_pos:]
    recovered = after_trough[after_trough >= peak_at_trough]
    if recovered.empty:
        return None
    recovery_pos = equity.index.get_loc(recovered.index[0])
    return int(recovery_pos - trough_pos)


def expectancy(trades: list[Trade]) -> float | None:
    """Average P&L per trade in currency terms - 'what do I expect to make,
    on average, each time I take this strategy's trade?'"""
    closed = [t for t in trades if t.pnl is not None]
    if not closed:
        return None
    return round(float(np.mean([t.pnl for t in closed])), 2)


def average_win_loss(trades: list[Trade]) -> dict:
    closed = [t for t in trades if t.pnl is not None]
    wins = [t.pnl for t in closed if t.pnl > 0]
    losses = [t.pnl for t in closed if t.pnl < 0]
    win_pcts = [t.pnl_pct for t in closed if t.pnl is not None and t.pnl > 0 and t.pnl_pct is not None]
    loss_pcts = [t.pnl_pct for t in closed if t.pnl is not None and t.pnl < 0 and t.pnl_pct is not None]
    median_pcts = [t.pnl_pct for t in closed if t.pnl_pct is not None]
    return {
        "average_win": round(float(np.mean(wins)), 2) if wins else None,
        "average_loss": round(float(np.mean(losses)), 2) if losses else None,
        "average_win_percent": round(float(np.mean(win_pcts)), 2) if win_pcts else None,
        "average_loss_percent": round(float(np.mean(loss_pcts)), 2) if loss_pcts else None,
        "median_trade_percent": round(float(np.median(median_pcts)), 2) if median_pcts else None,
    }


def exposure_percent(trades: list[Trade], trading_days: int) -> float | None:
    """Percentage of trading days the strategy held a position (vs. flat in
    cash). A HOLD-heavy model can have a strong Sharpe purely from sitting
    out volatility - exposure makes that visible.
    """
    if trading_days <= 0:
        return None
    days_in_position = 0
    for t in trades:
        if t.entry_date is None:
            continue
        start = pd.Timestamp(t.entry_date)
        end = pd.Timestamp(t.exit_date) if t.exit_date else None
        if end is None:
            continue  # still-open position's duration is already reflected in trading_days context by the caller
        days_in_position += max(0, np.busday_count(start.date(), end.date()))
    return round(min(100.0, days_in_position / trading_days * 100.0), 2)


def turnover_percent(trades: list[Trade], initial_capital: float) -> float | None:
    """Total traded notional (entries + exits) as a multiple of starting
    capital, expressed as a percentage - a rough proxy for how actively the
    strategy trades relative to its size.
    """
    if initial_capital <= 0 or not trades:
        return None
    notional = 0.0
    for t in trades:
        notional += t.entry_price * t.shares
        if t.exit_price is not None:
            notional += t.exit_price * t.shares
    return round(notional / initial_capital * 100.0, 2)


def beta_alpha_tracking_error(
    strategy_returns: pd.Series, benchmark_returns: pd.Series
) -> dict:
    """Beta/alpha/tracking-error/information-ratio of the strategy's daily
    returns against a benchmark's, aligned by date. Returns None fields when
    there isn't enough overlapping, varying data to compute them meaningfully.
    """
    aligned = pd.DataFrame({"strategy": strategy_returns, "benchmark": benchmark_returns}).dropna()
    if len(aligned) < 10:
        return {"beta": None, "alpha_percent": None, "tracking_error_percent": None, "information_ratio": None}

    bench_var = aligned["benchmark"].var(ddof=0)
    if bench_var == 0 or np.isnan(bench_var):
        beta = None
    else:
        cov = aligned["benchmark"].cov(aligned["strategy"])
        beta = float(cov / bench_var)

    daily_rf = RISK_FREE_RATE_ANNUAL / HIST_VOL_ANNUALIZATION
    if beta is not None:
        expected_daily = daily_rf + beta * (aligned["benchmark"].mean() - daily_rf)
        alpha_daily = aligned["strategy"].mean() - expected_daily
        alpha_percent = round(float(alpha_daily * HIST_VOL_ANNUALIZATION * 100.0), 2)
    else:
        alpha_percent = None

    diff = aligned["strategy"] - aligned["benchmark"]
    te_std = diff.std(ddof=0)
    tracking_error_percent = (
        round(float(te_std * np.sqrt(HIST_VOL_ANNUALIZATION) * 100.0), 2) if not np.isnan(te_std) else None
    )

    information_ratio = None
    if tracking_error_percent and tracking_error_percent > 0:
        annualized_diff = diff.mean() * HIST_VOL_ANNUALIZATION * 100.0
        information_ratio = round(float(annualized_diff / tracking_error_percent), 2)

    return {
        "beta": round(beta, 2) if beta is not None else None,
        "alpha_percent": alpha_percent,
        "tracking_error_percent": tracking_error_percent,
        "information_ratio": information_ratio,
    }
