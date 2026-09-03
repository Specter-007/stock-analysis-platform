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
