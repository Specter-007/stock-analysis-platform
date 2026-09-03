"""Paper-trading portfolio logic. SIMULATION ONLY - no real money, no
brokerage connection, no real orders. Valuation and execution both use
real, live-retrieved market quotes; nothing about the P&L numbers is
fabricated, but the "trades" themselves are purely virtual bookkeeping.

Long-only, no leverage. Every entry and exit is charged commission +
slippage (see `app.config.PAPER_TRADING_COMMISSION_BPS/SLIPPAGE_BPS`) as a
price haircut, and every closed trade reports gross P&L, fees, slippage,
and net P&L separately - never one opaque number.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.config import (
    MODEL_VERSION_CURRENT,
    PAPER_TRADING_COMMISSION_BPS,
    PAPER_TRADING_DEFAULT_MAX_POSITION_PERCENT,
    PAPER_TRADING_SLIPPAGE_BPS,
)
from app.indicators.compute import compute_indicator_frame, safe_float
from app.market.regime import classify_market_regime
from app.paper_trading.sizing import PositionSizingError, SizingRequest, calculate_shares
from app.paper_trading.store import load_portfolio, reset_portfolio, save_portfolio
from app.services import market_data
from app.services.exceptions import TickerNotFoundError
from app.signals import engine as signal_engine
from app.utils.validation import normalize_and_validate_ticker

EXIT_REASONS = (
    "MODEL_SELL",
    "STOP_LOSS",
    "TAKE_PROFIT",
    "TRAILING_STOP",
    "END_OF_TEST",
    "MANUAL_PAPER_EXIT",
)

_COST_RATE = (PAPER_TRADING_COMMISSION_BPS + PAPER_TRADING_SLIPPAGE_BPS) / 10_000.0


class PaperTradingError(ValueError):
    pass


@dataclass
class PositionView:
    ticker: str
    shares: float
    avg_entry_price: float
    current_price: float | None
    market_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_percent: float | None
    stop_loss_percent: float | None
    take_profit_percent: float | None
    trailing_stop_percent: float | None
    entry_signal: str | None
    entry_score: float | None
    entry_date: str | None


@dataclass
class PaperTradeView:
    date: str
    ticker: str
    action: str  # "BUY" | "SELL"
    shares: float
    price: float
    realized_pnl: float | None  # kept for backward compatibility; equals net_pnl on SELL rows
    gross_pnl: float | None = None
    fees: float | None = None
    slippage: float | None = None
    net_pnl: float | None = None
    exit_reason: str | None = None
    entry_signal: str | None = None
    entry_score: float | None = None
    exit_signal: str | None = None
    exit_score: float | None = None
    model_version: str | None = None
    market_regime: str | None = None


@dataclass
class PortfolioView:
    portfolio_id: str
    starting_capital: float
    cash: float
    invested_capital: float
    positions: list[PositionView] = field(default_factory=list)
    trades: list[PaperTradeView] = field(default_factory=list)
    current_value: float = 0.0
    total_return_percent: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    number_of_positions: int = 0
    exposure_percent: float = 0.0
    largest_position_percent: float = 0.0
    cash_percent: float = 100.0


@dataclass
class EquitySnapshotView:
    date: str
    recorded_at: str
    equity: float
    cash: float
    invested_value: float
    realized_pnl: float
    unrealized_pnl: float
    cumulative_return_percent: float | None
    benchmark_value: float | None
    daily_pnl: float | None
    previous_snapshot_date: str | None


@dataclass
class EquityHistoryView:
    portfolio_id: str
    starting_capital: float
    benchmark_ticker: str | None
    snapshots: list[EquitySnapshotView] = field(default_factory=list)


def _current_price(ticker: str) -> float | None:
    try:
        fast = market_data.fetch_fast_info_raw(ticker)
        return safe_float(fast.get("lastPrice"))
    except Exception:
        return None


def _current_signal_snapshot(ticker: str) -> tuple[str | None, float | None]:
    """Best-effort: the paper-trading journal is more useful with the
    signal/score at entry and exit, but a stock with too little history (or
    a transient data issue) must never block an otherwise-valid trade.
    """
    try:
        full_df, _ = market_data.get_full_daily_history(ticker)
        if len(full_df) < 20:
            return None, None
        indicator_df = compute_indicator_frame(full_df)
        result = signal_engine.evaluate(indicator_df)
        return result.signal, result.score
    except Exception:
        return None, None


def _current_market_regime() -> str | None:
    try:
        bench_df, _ = market_data.get_full_daily_history("SPY")
        indicator_df = compute_indicator_frame(bench_df)
        return classify_market_regime("SPY", indicator_df).regime
    except Exception:
        return None


def _fill_price(raw_price: float, action: str) -> float:
    return raw_price * (1 + _COST_RATE) if action == "BUY" else raw_price * (1 - _COST_RATE)


def _cost_breakdown(raw_entry: float, raw_exit: float, shares: float) -> dict:
    commission_rate = PAPER_TRADING_COMMISSION_BPS / 10_000.0
    slippage_rate = PAPER_TRADING_SLIPPAGE_BPS / 10_000.0
    fees = shares * (raw_entry + raw_exit) * commission_rate
    slippage = shares * (raw_entry + raw_exit) * slippage_rate
    gross_pnl = shares * (raw_exit - raw_entry)
    net_pnl = gross_pnl - fees - slippage
    return {
        "gross_pnl": round(gross_pnl, 2),
        "fees": round(fees, 2),
        "slippage": round(slippage, 2),
        "net_pnl": round(net_pnl, 2),
    }


BENCHMARK_TICKER = "SPY"


def _latest_real_trading_day() -> tuple[dt.date | None, float | None]:
    """The most recent trading day real market data actually exists for,
    keyed off the benchmark's own daily bars - never wall-clock "today",
    which could be a weekend/holiday with no real observation to record.
    Returns (None, None) if market data is unavailable right now, in which
    case no snapshot is recorded this cycle rather than fabricating one.
    """
    try:
        bench_df, _ = market_data.get_full_daily_history(BENCHMARK_TICKER)
        if bench_df.empty:
            return None, None
        last_row = bench_df.iloc[-1]
        return bench_df.index[-1].date(), safe_float(last_row["Close"])
    except Exception:
        return None, None


def _maybe_record_snapshot(portfolio_id: str, state: dict, view: PortfolioView) -> bool:
    """Appends today's equity observation if (a) a real trading day is
    available and (b) it hasn't already been recorded. Idempotent within a
    trading day: calling this many times (once per page load) never creates
    duplicate or updated entries for a day already captured - one immutable
    observation per real trading day, matching backtest cadence.
    """
    trading_day, benchmark_close = _latest_real_trading_day()
    if trading_day is None:
        return False

    snapshots = state.setdefault("equity_snapshots", [])
    trading_day_str = trading_day.isoformat()
    if snapshots and snapshots[-1]["date"] >= trading_day_str:
        return False

    basis = state.get("benchmark_basis")
    if basis is None and benchmark_close is not None:
        basis = {"date": trading_day_str, "price": benchmark_close}
        state["benchmark_basis"] = basis

    benchmark_value = None
    if basis and basis.get("price") and benchmark_close is not None:
        benchmark_value = state["starting_capital"] * (benchmark_close / basis["price"])

    previous = snapshots[-1] if snapshots else None
    daily_pnl = (view.current_value - previous["equity"]) if previous else None

    cumulative_return_pct = (
        (view.current_value / state["starting_capital"] - 1.0) * 100.0 if state["starting_capital"] else None
    )

    snapshots.append(
        {
            "date": trading_day_str,
            "recorded_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
            "equity": round(view.current_value, 2),
            "cash": round(view.cash, 2),
            "invested_value": round(view.current_value - view.cash, 2),
            "realized_pnl": round(view.realized_pnl, 2),
            "unrealized_pnl": round(view.unrealized_pnl, 2),
            "cumulative_return_percent": round(cumulative_return_pct, 2) if cumulative_return_pct is not None else None,
            "benchmark_value": round(benchmark_value, 2) if benchmark_value is not None else None,
            "daily_pnl": round(daily_pnl, 2) if daily_pnl is not None else None,
            "previous_snapshot_date": previous["date"] if previous else None,
        }
    )
    return True


def get_portfolio(portfolio_id: str) -> PortfolioView:
    _apply_pending_exits(portfolio_id)
    state = load_portfolio(portfolio_id)
    view = _build_view(state)
    if _maybe_record_snapshot(portfolio_id, state, view):
        save_portfolio(portfolio_id, state)
    return view


def get_equity_history(portfolio_id: str) -> EquityHistoryView:
    # Forces an opportunistic snapshot attempt for "today" before reading,
    # so a fresh page load always reflects the latest available trading day
    # rather than whatever was last recorded.
    get_portfolio(portfolio_id)
    state = load_portfolio(portfolio_id)
    return EquityHistoryView(
        portfolio_id=state["portfolio_id"],
        starting_capital=state["starting_capital"],
        benchmark_ticker=BENCHMARK_TICKER if state.get("benchmark_basis") else None,
        snapshots=[EquitySnapshotView(**s) for s in state.get("equity_snapshots", [])],
    )


def _build_view(state: dict) -> PortfolioView:
    positions: list[PositionView] = []
    invested_capital = 0.0
    unrealized_pnl_total = 0.0

    for ticker, pos in state["positions"].items():
        shares = pos["shares"]
        avg_entry = pos["avg_entry_price"]
        cost_basis = shares * avg_entry
        invested_capital += cost_basis

        current_price = _current_price(ticker)
        market_value = shares * current_price if current_price is not None else None
        unrealized = (market_value - cost_basis) if market_value is not None else None
        unrealized_pct = (unrealized / cost_basis * 100) if (unrealized is not None and cost_basis) else None

        if unrealized is not None:
            unrealized_pnl_total += unrealized

        positions.append(
            PositionView(
                ticker=ticker,
                shares=shares,
                avg_entry_price=avg_entry,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized,
                unrealized_pnl_percent=unrealized_pct,
                stop_loss_percent=pos.get("stop_loss_pct"),
                take_profit_percent=pos.get("take_profit_pct"),
                trailing_stop_percent=pos.get("trailing_stop_pct"),
                entry_signal=pos.get("entry_signal"),
                entry_score=pos.get("entry_score"),
                entry_date=pos.get("entry_date"),
            )
        )

    realized_pnl_total = sum(t.get("net_pnl") or t.get("realized_pnl") or 0.0 for t in state["trades"])
    positions_value = sum(p.market_value for p in positions if p.market_value is not None)
    current_value = state["cash"] + positions_value
    total_return_pct = (
        (current_value / state["starting_capital"] - 1.0) * 100.0 if state["starting_capital"] else 0.0
    )

    largest_position_pct = 0.0
    if current_value > 0:
        for p in positions:
            if p.market_value is not None:
                largest_position_pct = max(largest_position_pct, p.market_value / current_value * 100.0)

    exposure_pct = (positions_value / current_value * 100.0) if current_value > 0 else 0.0
    cash_pct = (state["cash"] / current_value * 100.0) if current_value > 0 else 100.0

    return PortfolioView(
        portfolio_id=state["portfolio_id"],
        starting_capital=state["starting_capital"],
        cash=round(state["cash"], 2),
        invested_capital=round(invested_capital, 2),
        positions=positions,
        trades=[PaperTradeView(**t) for t in state["trades"]],
        current_value=round(current_value, 2),
        total_return_percent=round(total_return_pct, 2),
        realized_pnl=round(realized_pnl_total, 2),
        unrealized_pnl=round(unrealized_pnl_total, 2),
        number_of_positions=len(positions),
        exposure_percent=round(exposure_pct, 2),
        largest_position_percent=round(largest_position_pct, 2),
        cash_percent=round(cash_pct, 2),
    )


def _record_trade(state: dict, **fields) -> None:
    state["trades"].append({"date": dt.datetime.now(tz=dt.timezone.utc).isoformat(), **fields})


def _close_position(
    state: dict, ticker: str, shares_to_close: float, raw_price: float, exit_reason: str
) -> None:
    positions = state["positions"]
    existing = positions[ticker]
    fill_price = _fill_price(raw_price, "SELL")
    proceeds = shares_to_close * fill_price

    raw_entry = existing.get("avg_entry_price_raw", existing["avg_entry_price"])
    costs = _cost_breakdown(raw_entry, raw_price, shares_to_close)

    exit_signal, exit_score = _current_signal_snapshot(ticker)

    remaining = existing["shares"] - shares_to_close
    if remaining <= 1e-9:
        del positions[ticker]
    else:
        existing["shares"] = remaining

    state["cash"] += proceeds

    _record_trade(
        state,
        ticker=ticker,
        action="SELL",
        shares=shares_to_close,
        price=fill_price,
        realized_pnl=costs["net_pnl"],
        gross_pnl=costs["gross_pnl"],
        fees=costs["fees"],
        slippage=costs["slippage"],
        net_pnl=costs["net_pnl"],
        exit_reason=exit_reason,
        entry_signal=existing.get("entry_signal"),
        entry_score=existing.get("entry_score"),
        exit_signal=exit_signal,
        exit_score=exit_score,
        model_version=existing.get("entry_model_version", MODEL_VERSION_CURRENT),
        market_regime=existing.get("entry_regime"),
    )


def _apply_pending_exits(portfolio_id: str) -> None:
    """Checks every open position's stop-loss/take-profit/trailing-stop
    against the CURRENT live price and auto-closes any that trigger. Applied
    every time the portfolio is loaded, so a trigger is caught on the next
    view rather than requiring a background process.
    """
    state = load_portfolio(portfolio_id)
    positions = state["positions"]
    changed = False

    for ticker in list(positions.keys()):
        pos = positions[ticker]
        price = _current_price(ticker)
        if price is None:
            continue

        if price > pos.get("highest_price_since_entry", pos["avg_entry_price_raw"]):
            pos["highest_price_since_entry"] = price
            changed = True

        raw_entry = pos.get("avg_entry_price_raw", pos["avg_entry_price"])
        stop_loss_pct = pos.get("stop_loss_pct")
        take_profit_pct = pos.get("take_profit_pct")
        trailing_stop_pct = pos.get("trailing_stop_pct")

        exit_reason = None
        if stop_loss_pct and price <= raw_entry * (1 - stop_loss_pct / 100.0):
            exit_reason = "STOP_LOSS"
        elif take_profit_pct and price >= raw_entry * (1 + take_profit_pct / 100.0):
            exit_reason = "TAKE_PROFIT"
        elif trailing_stop_pct and price <= pos["highest_price_since_entry"] * (1 - trailing_stop_pct / 100.0):
            exit_reason = "TRAILING_STOP"

        if exit_reason:
            _close_position(state, ticker, pos["shares"], price, exit_reason)
            changed = True

    if changed:
        save_portfolio(portfolio_id, state)


def execute_trade(
    portfolio_id: str,
    ticker: str,
    action: str,
    shares: float | None = None,
    sizing_mode: str | None = None,
    capital_percent: float | None = None,
    risk_percent: float | None = None,
    stop_loss_percent: float | None = None,
    take_profit_percent: float | None = None,
    trailing_stop_percent: float | None = None,
    max_position_percent: float = PAPER_TRADING_DEFAULT_MAX_POSITION_PERCENT,
) -> PortfolioView:
    _apply_pending_exits(portfolio_id)

    ticker = normalize_and_validate_ticker(ticker)
    action = action.upper()
    if action not in ("BUY", "SELL"):
        raise PaperTradingError("Action must be 'BUY' or 'SELL'.")

    raw_price = _current_price(ticker)
    if raw_price is None:
        raise TickerNotFoundError(ticker)

    state = load_portfolio(portfolio_id)
    positions = state["positions"]

    if action == "BUY":
        view_before = _build_view(state)
        if shares is None:
            mode = sizing_mode or "FIXED_SHARES"
            try:
                shares = calculate_shares(
                    SizingRequest(
                        mode=mode,
                        price=raw_price,
                        portfolio_equity=view_before.current_value,
                        available_cash=state["cash"],
                        capital_percent=capital_percent,
                        risk_percent=risk_percent,
                        stop_loss_percent=stop_loss_percent,
                        max_position_percent=max_position_percent,
                    )
                )
            except PositionSizingError as exc:
                raise PaperTradingError(str(exc)) from exc
        if shares <= 0:
            raise PaperTradingError("Shares must be a positive number.")

        fill_price = _fill_price(raw_price, "BUY")
        cost = shares * fill_price
        if cost > state["cash"] + 1e-6:
            raise PaperTradingError(
                f"Insufficient cash: trade costs ${cost:,.2f} but only ${state['cash']:,.2f} is available."
            )

        entry_signal, entry_score = _current_signal_snapshot(ticker)
        entry_regime = _current_market_regime()

        existing = positions.get(ticker)
        if existing:
            total_shares = existing["shares"] + shares
            existing["avg_entry_price"] = (
                existing["shares"] * existing["avg_entry_price"] + shares * fill_price
            ) / total_shares
            existing["avg_entry_price_raw"] = (
                existing["shares"] * existing.get("avg_entry_price_raw", existing["avg_entry_price"])
                + shares * raw_price
            ) / total_shares
            existing["shares"] = total_shares
            existing["highest_price_since_entry"] = max(existing.get("highest_price_since_entry", raw_price), raw_price)
        else:
            positions[ticker] = {
                "shares": shares,
                "avg_entry_price": fill_price,
                "avg_entry_price_raw": raw_price,
                "highest_price_since_entry": raw_price,
                "stop_loss_pct": stop_loss_percent,
                "take_profit_pct": take_profit_percent,
                "trailing_stop_pct": trailing_stop_percent,
                "entry_signal": entry_signal,
                "entry_score": entry_score,
                "entry_regime": entry_regime,
                "entry_model_version": MODEL_VERSION_CURRENT,
                "entry_date": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
            }
        state["cash"] -= cost

        _record_trade(
            state,
            ticker=ticker,
            action="BUY",
            shares=shares,
            price=fill_price,
            realized_pnl=None,
            entry_signal=entry_signal,
            entry_score=entry_score,
            model_version=MODEL_VERSION_CURRENT,
            market_regime=entry_regime,
        )

    else:  # SELL - always a MANUAL_PAPER_EXIT when called directly via the API
        existing = positions.get(ticker)
        held = existing["shares"] if existing else 0.0
        if shares is None:
            shares = held
        if shares > held + 1e-6:
            raise PaperTradingError(f"Cannot sell {shares} shares of {ticker}; only {held} are held.")
        if shares <= 0:
            raise PaperTradingError("Shares must be a positive number.")
        _close_position(state, ticker, shares, raw_price, "MANUAL_PAPER_EXIT")

    save_portfolio(portfolio_id, state)
    return get_portfolio(portfolio_id)


def close_all_positions(portfolio_id: str, exit_reason: str = "END_OF_TEST") -> PortfolioView:
    """Liquidates every open position at the current live price - used, for
    example, to mark a research session's end without leaving positions
    open indefinitely."""
    _apply_pending_exits(portfolio_id)
    state = load_portfolio(portfolio_id)
    for ticker in list(state["positions"].keys()):
        price = _current_price(ticker)
        if price is None:
            continue
        _close_position(state, ticker, state["positions"][ticker]["shares"], price, exit_reason)
    save_portfolio(portfolio_id, state)
    return get_portfolio(portfolio_id)


def reset(portfolio_id: str, starting_capital: float | None = None) -> PortfolioView:
    reset_portfolio(portfolio_id, starting_capital)
    return get_portfolio(portfolio_id)
