"""Portfolio-level (multi-ticker) backtesting.

This is an ALLOCATION layer on top of the exact same per-ticker decisions
every single-ticker backtest already makes - it calls the same
`app.signals.engine.evaluate` over the same `app.indicators.compute.
compute_indicator_frame` as `app.backtesting.engine.run_backtest`, and never
re-implements or duplicates that logic. What this module adds is: which of
several tickers to hold at any time, at what weight, rebalanced how often,
and under what portfolio-level constraints.

Long-only, no leverage: invested weight across all positions plus cash
always equals the portfolio's own equity; a position is never shorted and
total exposure never exceeds 100%.

No-look-ahead contract (same as the single-ticker engine): target weights
for a rebalance are decided from data available at day T's close; the
resulting trades execute at day T+1's open with a transaction-cost/slippage
price haircut. Between rebalances, positions are marked to market only -
no new orders are placed.
"""
from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.backtesting import metrics as m
from app.config import MODEL_VERSION_CURRENT
from app.indicators.compute import compute_indicator_frame
from app.services import market_data
from app.services.exceptions import InsufficientHistoryError
from app.signals import engine as signal_engine

MIN_SIM_TRADING_DAYS = 30
MIN_TRADES_FOR_RELIABLE_METRICS = 5
_EPS = 1e-9

ALLOCATION_METHODS = ("EQUAL_WEIGHT", "FIXED_WEIGHT", "SIGNAL_WEIGHTED", "RISK_WEIGHTED")
REBALANCE_FREQUENCIES = ("DAILY", "WEEKLY", "MONTHLY")

ALLOCATION_METHODOLOGY = {
    "EQUAL_WEIGHT": "Investable capital split equally across every ticker currently signaling BUY/STRONG_BUY.",
    "FIXED_WEIGHT": (
        "Caller-supplied target weights, renormalized across only the tickers currently signaling "
        "BUY/STRONG_BUY (a ticker with a fixed weight but no active BUY signal holds 0% until its "
        "signal turns on)."
    ),
    "SIGNAL_WEIGHTED": (
        "Weight proportional to each eligible ticker's own 0-100 signal score (all non-negative, so "
        "this is a well-defined proportional split, not a risk-adjusted optimization)."
    ),
    "RISK_WEIGHTED": (
        "Inverse-historical-volatility weighting among eligible tickers (weight_i proportional to "
        "1/HIST_VOL_20_i) - a standard, well-defined heuristic, not a full risk-parity optimization."
    ),
}

REBALANCE_METHODOLOGY = (
    "DAILY re-evaluates and re-targets every trading day. WEEKLY/MONTHLY only re-target on the first "
    "trading day of each calendar week/month; on other days, existing positions are marked to market "
    "but not traded. All rebalance decisions use data available at that day's close and execute at "
    "the NEXT trading day's open, with the same transaction-cost/slippage haircut as single-ticker "
    "backtests - never same-day execution on the signal that produced the decision."
)

CONSTRAINT_METHODOLOGY = (
    "max_position_weight caps any single name and redistributes the excess proportionally across "
    "other held names (a few waterfall passes, not a full optimizer). min_position_weight drops a "
    "name entirely if it can't be funded at least that much, rather than forcing it up - the freed "
    "weight becomes cash. sector_cap scales down every name in an over-cap sector proportionally; "
    "freed capital becomes cash rather than being redistributed to other sectors (a conservative "
    "simplification, documented here rather than silently assumed). cash_allocation is a minimum "
    "cash buffer that no rebalance is ever allowed to invest below."
)


@dataclass
class PortfolioConstraints:
    max_position_weight_percent: float = 100.0
    min_position_weight_percent: float = 0.0
    max_holdings: int | None = None
    cash_allocation_percent: float = 0.0
    sector_cap_percent: float | None = None


@dataclass
class PortfolioEquityPoint:
    date: str
    equity: float


@dataclass
class PortfolioHoldingSnapshot:
    date: str
    ticker: str
    weight_percent: float
    shares: float
    price: float
    market_value: float


@dataclass
class PortfolioBacktestResult:
    tickers: list[str]
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    allocation_method: str
    rebalance_frequency: str
    total_return_percent: float | None
    equal_weight_buy_hold_return_percent: float | None
    benchmark_ticker: str | None
    benchmark_return_percent: float | None
    max_drawdown_percent: float | None
    sharpe_ratio: float | None
    trading_days: int
    number_of_rebalances: int
    equity_curve: list[PortfolioEquityPoint] = field(default_factory=list)
    equal_weight_buy_hold_curve: list[PortfolioEquityPoint] = field(default_factory=list)
    benchmark_curve: list[PortfolioEquityPoint] = field(default_factory=list)
    drawdown_curve: list[PortfolioEquityPoint] = field(default_factory=list)
    holdings_history: list[PortfolioHoldingSnapshot] = field(default_factory=list)
    advanced_metrics: dict = field(default_factory=dict)
    risk_analytics: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    excluded_tickers: dict[str, str] = field(default_factory=dict)
    methodology: dict[str, str] = field(default_factory=dict)


def _sector_for(ticker: str) -> str:
    try:
        overview, _ = market_data.get_overview(ticker)
        return overview.get("sector") or "Unknown"
    except Exception:
        return "Unknown"


def _rebalance_dates(all_dates: list[dt.date], frequency: str) -> set[dt.date]:
    if frequency == "DAILY":
        return set(all_dates)
    if frequency not in ("WEEKLY", "MONTHLY"):
        raise ValueError(f"Unknown rebalance frequency: {frequency}")

    seen: set[tuple] = set()
    out: set[dt.date] = set()
    for d in all_dates:
        key = d.isocalendar()[:2] if frequency == "WEEKLY" else (d.year, d.month)
        if key not in seen:
            seen.add(key)
            out.add(d)
    return out


def _clip_and_renormalize(weights: dict[str, float], max_w: float, min_w: float) -> dict[str, float]:
    weights = dict(weights)
    for _ in range(5):
        over = {t: w for t, w in weights.items() if w > max_w + _EPS}
        if not over:
            break
        excess = sum(w - max_w for w in over.values())
        for t in over:
            weights[t] = max_w
        under_cap = {t: w for t, w in weights.items() if t not in over}
        under_total = sum(under_cap.values())
        if under_total <= _EPS:
            break
        for t in under_cap:
            weights[t] += excess * (under_cap[t] / under_total)

    if min_w > 0:
        weights = {t: w for t, w in weights.items() if w >= min_w - _EPS}
    return weights


def _apply_sector_caps(weights: dict[str, float], sector_of: dict[str, str], cap: float) -> dict[str, float]:
    sector_totals: dict[str, float] = {}
    for t, w in weights.items():
        s = sector_of.get(t, "Unknown")
        sector_totals[s] = sector_totals.get(s, 0.0) + w

    adjusted = dict(weights)
    for s, total in sector_totals.items():
        if total > cap + _EPS:
            scale = cap / total
            for t, w in weights.items():
                if sector_of.get(t, "Unknown") == s:
                    adjusted[t] = w * scale
    return adjusted


def _target_weights(
    eligible_scores: dict[str, float],
    vol_of: dict[str, float | None],
    method: str,
    fixed_weights: dict[str, float] | None,
    constraints: PortfolioConstraints,
    sector_of: dict[str, str],
) -> dict[str, float]:
    if not eligible_scores:
        return {}

    eligible = list(eligible_scores.keys())
    if constraints.max_holdings is not None and len(eligible) > constraints.max_holdings:
        eligible = sorted(eligible, key=lambda t: eligible_scores[t], reverse=True)[: constraints.max_holdings]

    investable = max(0.0, 1.0 - constraints.cash_allocation_percent / 100.0)
    n = len(eligible)

    if method == "EQUAL_WEIGHT":
        raw = {t: investable / n for t in eligible}
    elif method == "FIXED_WEIGHT":
        fixed_weights = fixed_weights or {}
        subset = {t: max(0.0, fixed_weights.get(t, 0.0)) for t in eligible}
        total = sum(subset.values())
        raw = {t: (w / total * investable if total > 0 else investable / n) for t, w in subset.items()}
    elif method == "SIGNAL_WEIGHTED":
        scores = {t: max(0.0, eligible_scores[t]) for t in eligible}
        total_score = sum(scores.values())
        raw = {t: (s / total_score * investable if total_score > 0 else investable / n) for t, s in scores.items()}
    elif method == "RISK_WEIGHTED":
        inv_vol = {t: (1.0 / vol_of[t]) for t in eligible if vol_of.get(t) and vol_of[t] > 0}
        total_inv = sum(inv_vol.values())
        if total_inv > 0:
            raw = {t: inv_vol[t] / total_inv * investable for t in inv_vol}
        else:
            raw = {t: investable / n for t in eligible}
    else:
        raise ValueError(f"Unknown allocation method: {method}")

    raw = _clip_and_renormalize(raw, constraints.max_position_weight_percent / 100.0, constraints.min_position_weight_percent / 100.0)
    if constraints.sector_cap_percent is not None:
        raw = _apply_sector_caps(raw, sector_of, constraints.sector_cap_percent / 100.0)
    return raw


def run_portfolio_backtest(
    tickers: list[str],
    price_data: dict[str, pd.DataFrame],
    start_date: dt.date,
    end_date: dt.date,
    initial_capital: float,
    transaction_cost_bps: float,
    slippage_bps: float,
    allocation_method: str = "EQUAL_WEIGHT",
    rebalance_frequency: str = "MONTHLY",
    constraints: PortfolioConstraints | None = None,
    fixed_weights: dict[str, float] | None = None,
    model_version: str = MODEL_VERSION_CURRENT,
    benchmark_ticker: str | None = None,
    benchmark_price_df: pd.DataFrame | None = None,
) -> PortfolioBacktestResult:
    if allocation_method not in ALLOCATION_METHODS:
        raise ValueError(f"Unknown allocation method: {allocation_method}")
    if rebalance_frequency not in REBALANCE_FREQUENCIES:
        raise ValueError(f"Unknown rebalance frequency: {rebalance_frequency}")

    constraints = constraints or PortfolioConstraints()
    warnings: list[str] = []
    excluded_tickers: dict[str, str] = {}

    indicator_data: dict[str, pd.DataFrame] = {}
    for t in tickers:
        df = price_data.get(t)
        if df is None or df.empty:
            excluded_tickers[t] = "No price data available."
            continue
        indicator_data[t] = compute_indicator_frame(df)

    active_tickers = list(indicator_data.keys())
    if not active_tickers:
        raise InsufficientHistoryError(",".join(tickers), 0, MIN_SIM_TRADING_DAYS)

    date_to_pos: dict[str, dict[dt.date, int]] = {
        t: {ts.date(): i for i, ts in enumerate(df.index)} for t, df in indicator_data.items()
    }

    all_dates_set: set[dt.date] = set()
    for t, dtp in date_to_pos.items():
        all_dates_set |= {d for d in dtp if start_date <= d <= end_date}
    all_dates = sorted(all_dates_set)

    if len(all_dates) < MIN_SIM_TRADING_DAYS:
        raise InsufficientHistoryError(",".join(tickers), len(all_dates), MIN_SIM_TRADING_DAYS)

    with ThreadPoolExecutor(max_workers=min(8, len(active_tickers))) as pool:
        sector_list = list(pool.map(_sector_for, active_tickers))
    sector_of = dict(zip(active_tickers, sector_list))

    cost_rate = (transaction_cost_bps + slippage_bps) / 10_000.0
    rebal_dates = _rebalance_dates(all_dates, rebalance_frequency)

    cash = initial_capital
    shares: dict[str, float] = {t: 0.0 for t in active_tickers}
    last_price: dict[str, float] = {}
    equity_points: list[tuple[dt.date, float]] = []
    holdings_history: list[PortfolioHoldingSnapshot] = []
    number_of_rebalances = 0
    pending: dict[str, float] | None = None  # ticker -> target weight, decided at prior close
    stale_tickers_warned: set[str] = set()

    def _row(t: str, date: dt.date):
        pos = date_to_pos[t].get(date)
        return None if pos is None else indicator_data[t].iloc[pos]

    for date in all_dates:
        # 1. Execute any pending rebalance at today's OPEN.
        if pending is not None:
            open_prices: dict[str, float] = {}
            for t in active_tickers:
                row = _row(t, date)
                if row is not None:
                    open_prices[t] = float(row["Open"])
                elif t in last_price:
                    open_prices[t] = last_price[t]

            # The dollar basis for target weights is THIS MOMENT's actual portfolio value
            # (cash + holdings marked at today's open) - not the decision day's stale close
            # snapshot. Using a stale basis would make a holding that is ALREADY exactly at
            # its (unchanged) target weight look "underfunded" purely from overnight price
            # drift between the decision close and this execution open, with no cash to fund
            # a purely illusory gap. Sizing off the execution-moment equity means a no-op
            # rebalance (target == current allocation) produces zero trades, as it should.
            execution_equity = cash + sum(
                shares[t] * open_prices.get(t, last_price.get(t, 0.0)) for t in active_tickers
            )
            target_dollars = {t: execution_equity * w for t, w in pending.items()}
            current_dollars = {t: shares[t] * open_prices.get(t, last_price.get(t, 0.0)) for t in active_tickers}

            # Sells first, so their proceeds can fund buys without needing margin.
            for t in active_tickers:
                target = target_dollars.get(t, 0.0)
                current = current_dollars.get(t, 0.0)
                if target < current - _EPS and t in open_prices:
                    delta_dollars = current - target
                    fill_price = open_prices[t] * (1 - cost_rate)
                    delta_shares = delta_dollars / open_prices[t] if open_prices[t] > 0 else 0.0
                    delta_shares = min(delta_shares, shares[t])
                    shares[t] -= delta_shares
                    cash += delta_shares * fill_price

            buy_orders: dict[str, float] = {}
            for t in active_tickers:
                target = target_dollars.get(t, 0.0)
                current = shares[t] * open_prices.get(t, last_price.get(t, 0.0))
                if target > current + _EPS and t in open_prices:
                    buy_orders[t] = target - current

            # Each dollar of `buy_orders` is cash actually spent (the cost/slippage haircut is
            # already priced into how many shares that cash buys, via fill_price below) - so the
            # total cash required is simply the sum of the order dollar amounts.
            total_buy_cost = sum(buy_orders.values())
            scale = 1.0 if total_buy_cost <= cash or total_buy_cost <= 0 else cash / total_buy_cost
            # A shortfall under ~1% is just the transaction-cost/slippage friction on the
            # rotation itself (selling and buying both cost a few bps) - expected on every
            # sell-to-buy rotation, not a real funding problem worth surfacing as a warning.
            if scale < 0.99:
                warnings.append(
                    f"Insufficient cash to fully fund the rebalance on {date.isoformat()}; buy orders scaled to {scale * 100:.1f}%."
                )

            for t, dollars in buy_orders.items():
                fill_price = open_prices[t] * (1 + cost_rate)
                spend = dollars * scale
                delta_shares = spend / fill_price if fill_price > 0 else 0.0
                shares[t] += delta_shares
                cash -= delta_shares * fill_price

            cash = max(cash, 0.0)
            number_of_rebalances += 1
            pending = None

        # 2. Mark to market at today's CLOSE.
        equity = cash
        for t in active_tickers:
            row = _row(t, date)
            if row is not None:
                last_price[t] = float(row["Close"])
            elif t not in last_price:
                continue
            elif t not in stale_tickers_warned:
                stale_tickers_warned.add(t)
                warnings.append(f"'{t}' had no price data on some trading days in range; last known price was carried forward.")
            price = last_price.get(t)
            if price is not None:
                equity += shares[t] * price

        equity_points.append((date, equity))

        for t in active_tickers:
            if shares[t] > _EPS and t in last_price:
                mv = shares[t] * last_price[t]
                holdings_history.append(
                    PortfolioHoldingSnapshot(
                        date=date.isoformat(),
                        ticker=t,
                        weight_percent=round(mv / equity * 100.0, 2) if equity > 0 else 0.0,
                        shares=round(shares[t], 6),
                        price=round(last_price[t], 2),
                        market_value=round(mv, 2),
                    )
                )

        # 3. If today is a rebalance date, decide target weights (using data
        # through today's close) for execution at the NEXT trading day's open.
        if date in rebal_dates:
            scores: dict[str, float] = {}
            vols: dict[str, float | None] = {}
            for t in active_tickers:
                pos = date_to_pos[t].get(date)
                if pos is None:
                    continue
                try:
                    hist_slice = indicator_data[t].iloc[: pos + 1]
                    sig = signal_engine.evaluate(hist_slice, model_version=model_version)
                except Exception:
                    continue
                if sig.signal in ("BUY", "STRONG_BUY"):
                    scores[t] = sig.score
                vol = indicator_data[t].iloc[pos].get("HIST_VOL_20")
                vols[t] = float(vol) if vol is not None and not pd.isna(vol) else None

            pending = _target_weights(scores, vols, allocation_method, fixed_weights, constraints, sector_of)

    final_capital = equity_points[-1][1]
    equity_series = pd.Series([e for _, e in equity_points], index=[d for d, _ in equity_points])
    daily_returns = equity_series.pct_change()
    trading_days = len(equity_series)

    # Equal-weight buy & hold comparison: buy every active ticker equally at
    # day-1 open, never rebalanced or traded again.
    ew_shares: dict[str, float] = {}
    first_date = all_dates[0]
    per_ticker_capital = initial_capital / len(active_tickers)
    for t in active_tickers:
        row = _row(t, first_date)
        if row is not None and float(row["Open"]) > 0:
            entry_price = float(row["Open"]) * (1 + cost_rate)
            ew_shares[t] = per_ticker_capital / entry_price
    ew_curve: list[tuple[dt.date, float]] = []
    ew_last_price: dict[str, float] = {}
    for date in all_dates:
        val = 0.0
        for t in active_tickers:
            row = _row(t, date)
            if row is not None:
                ew_last_price[t] = float(row["Close"])
            price = ew_last_price.get(t)
            if price is not None:
                val += ew_shares.get(t, 0.0) * price
        ew_curve.append((date, val))
    ew_return = m.total_return(initial_capital, ew_curve[-1][1]) if ew_curve else None

    benchmark_curve_points: list[PortfolioEquityPoint] = []
    benchmark_return = None
    if benchmark_ticker and benchmark_price_df is not None and not benchmark_price_df.empty:
        bench_mask = (benchmark_price_df.index.date >= all_dates[0]) & (benchmark_price_df.index.date <= all_dates[-1])
        bench_slice = benchmark_price_df.loc[bench_mask]
        if not bench_slice.empty:
            entry_price = float(bench_slice.iloc[0]["Open"]) * (1 + cost_rate)
            bench_shares = initial_capital / entry_price if entry_price > 0 else 0.0
            bench_series = bench_shares * bench_slice["Close"]
            benchmark_return = m.total_return(initial_capital, float(bench_series.iloc[-1]))
            benchmark_curve_points = [
                PortfolioEquityPoint(date=str(ts.date()), equity=round(float(v), 2)) for ts, v in bench_series.items()
            ]
        else:
            warnings.append(f"No benchmark data available for '{benchmark_ticker}' in the requested range.")

    max_dd_pct = m.max_drawdown_percent(equity_series)
    cagr_pct = m.cagr(initial_capital, final_capital, trading_days)
    drawdown_series = (equity_series - equity_series.cummax()) / equity_series.cummax() * 100.0

    advanced_metrics = {
        "cagr_percent": round(cagr_pct, 2) if cagr_pct is not None else None,
        "annualized_volatility_percent": m.annualized_volatility_percent(daily_returns),
        "sortino_ratio": (round(v, 3) if (v := m.sortino_ratio(daily_returns)) is not None else None),
        "calmar_ratio": m.calmar_ratio(cagr_pct, max_dd_pct),
        "average_drawdown_percent": m.average_drawdown_percent(equity_series),
        "max_drawdown_recovery_days": m.max_drawdown_recovery_days(equity_series),
    }

    # Risk analytics: correlation from REAL historical daily RETURNS (not
    # price levels), plus a snapshot of the final rebalance's composition.
    returns_frame = pd.DataFrame(
        {t: indicator_data[t]["Close"].pct_change() for t in active_tickers}
    ).dropna(how="all")
    correlation_matrix = None
    if returns_frame.shape[1] >= 2 and len(returns_frame.dropna()) >= 10:
        corr = returns_frame.corr()
        correlation_matrix = {t: {u: (round(float(v), 3) if not pd.isna(v) else None) for u, v in row.items()} for t, row in corr.items()}

    final_date = all_dates[-1]
    final_holdings = [h for h in holdings_history if h.date == final_date.isoformat()]
    final_holdings_sorted = sorted(final_holdings, key=lambda h: h.market_value, reverse=True)
    sector_exposure: dict[str, float] = {}
    for h in final_holdings:
        s = sector_of.get(h.ticker, "Unknown")
        sector_exposure[s] = sector_exposure.get(s, 0.0) + h.weight_percent

    risk_analytics = {
        "exposure_percent": round(sum(h.weight_percent for h in final_holdings), 2),
        "cash_percent": round(max(0.0, 100.0 - sum(h.weight_percent for h in final_holdings)), 2),
        "largest_position_percent": round(final_holdings_sorted[0].weight_percent, 2) if final_holdings_sorted else 0.0,
        "top_3_concentration_percent": round(sum(h.weight_percent for h in final_holdings_sorted[:3]), 2),
        "sector_concentration_percent": {s: round(v, 2) for s, v in sector_exposure.items()},
        "correlation_matrix": correlation_matrix,
        "number_of_holdings": len(final_holdings),
    }

    if len(active_tickers) < 2:
        warnings.append("Only one ticker had usable data; correlation and diversification analytics are N/A.")

    result = PortfolioBacktestResult(
        tickers=active_tickers,
        start_date=str(all_dates[0]),
        end_date=str(all_dates[-1]),
        initial_capital=round(initial_capital, 2),
        final_capital=round(final_capital, 2),
        allocation_method=allocation_method,
        rebalance_frequency=rebalance_frequency,
        total_return_percent=(round(v, 2) if (v := m.total_return(initial_capital, final_capital)) is not None else None),
        equal_weight_buy_hold_return_percent=round(ew_return, 2) if ew_return is not None else None,
        benchmark_ticker=benchmark_ticker,
        benchmark_return_percent=round(benchmark_return, 2) if benchmark_return is not None else None,
        max_drawdown_percent=max_dd_pct,
        sharpe_ratio=(round(sr, 3) if (sr := m.sharpe_ratio(daily_returns)) is not None else None),
        trading_days=trading_days,
        number_of_rebalances=number_of_rebalances,
        equity_curve=[PortfolioEquityPoint(date=str(d), equity=round(e, 2)) for d, e in equity_points],
        equal_weight_buy_hold_curve=[PortfolioEquityPoint(date=str(d), equity=round(v, 2)) for d, v in ew_curve],
        benchmark_curve=benchmark_curve_points,
        drawdown_curve=[PortfolioEquityPoint(date=str(d), equity=round(float(v), 2)) for d, v in drawdown_series.items()],
        holdings_history=holdings_history,
        advanced_metrics=advanced_metrics,
        risk_analytics=risk_analytics,
        warnings=warnings,
        excluded_tickers=excluded_tickers,
        methodology={
            "allocation": ALLOCATION_METHODOLOGY[allocation_method],
            "rebalancing": REBALANCE_METHODOLOGY,
            "constraints": CONSTRAINT_METHODOLOGY,
            "correlation": "Pairwise Pearson correlation of each holding's daily percentage RETURNS over the backtest window (not price levels, which are non-stationary and produce spurious correlation).",
        },
    )
    return result
