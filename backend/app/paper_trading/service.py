"""Paper-trading portfolio logic. SIMULATION ONLY - no real money, no
brokerage connection, no real orders. Valuation uses real, live-retrieved
market quotes; nothing about the P&L numbers is fabricated, but the
"trades" themselves are purely virtual bookkeeping.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.indicators.compute import safe_float
from app.paper_trading.store import load_portfolio, reset_portfolio, save_portfolio
from app.services import market_data
from app.services.exceptions import TickerNotFoundError
from app.utils.validation import normalize_and_validate_ticker


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


@dataclass
class PaperTradeView:
    date: str
    ticker: str
    action: str  # "BUY" | "SELL"
    shares: float
    price: float
    realized_pnl: float | None


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


def _current_price(ticker: str) -> float | None:
    try:
        fast = market_data.fetch_fast_info_raw(ticker)
        return safe_float(fast.get("lastPrice"))
    except Exception:
        return None


def get_portfolio(portfolio_id: str) -> PortfolioView:
    state = load_portfolio(portfolio_id)

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
            )
        )

    realized_pnl_total = sum(t.get("realized_pnl") or 0.0 for t in state["trades"])
    positions_value = sum(p.market_value for p in positions if p.market_value is not None)
    current_value = state["cash"] + positions_value
    total_return_pct = (
        (current_value / state["starting_capital"] - 1.0) * 100.0 if state["starting_capital"] else 0.0
    )

    return PortfolioView(
        portfolio_id=state["portfolio_id"],
        starting_capital=state["starting_capital"],
        cash=state["cash"],
        invested_capital=round(invested_capital, 2),
        positions=positions,
        trades=[PaperTradeView(**t) for t in state["trades"]],
        current_value=round(current_value, 2),
        total_return_percent=round(total_return_pct, 2),
        realized_pnl=round(realized_pnl_total, 2),
        unrealized_pnl=round(unrealized_pnl_total, 2),
    )


def execute_trade(portfolio_id: str, ticker: str, action: str, shares: float) -> PortfolioView:
    ticker = normalize_and_validate_ticker(ticker)
    action = action.upper()
    if action not in ("BUY", "SELL"):
        raise PaperTradingError("Action must be 'BUY' or 'SELL'.")
    if shares <= 0:
        raise PaperTradingError("Shares must be a positive number.")

    price = _current_price(ticker)
    if price is None:
        raise TickerNotFoundError(ticker)

    state = load_portfolio(portfolio_id)
    positions = state["positions"]
    realized_pnl = None

    if action == "BUY":
        cost = shares * price
        if cost > state["cash"] + 1e-6:
            raise PaperTradingError(
                f"Insufficient cash: trade costs ${cost:,.2f} but only ${state['cash']:,.2f} is available."
            )
        existing = positions.get(ticker)
        if existing:
            total_shares = existing["shares"] + shares
            existing["avg_entry_price"] = (
                existing["shares"] * existing["avg_entry_price"] + shares * price
            ) / total_shares
            existing["shares"] = total_shares
        else:
            positions[ticker] = {"shares": shares, "avg_entry_price": price}
        state["cash"] -= cost

    else:  # SELL
        existing = positions.get(ticker)
        held = existing["shares"] if existing else 0.0
        if shares > held + 1e-6:
            raise PaperTradingError(f"Cannot sell {shares} shares of {ticker}; only {held} are held.")
        proceeds = shares * price
        realized_pnl = (price - existing["avg_entry_price"]) * shares
        remaining = held - shares
        if remaining <= 1e-9:
            del positions[ticker]
        else:
            existing["shares"] = remaining
        state["cash"] += proceeds

    state["trades"].append(
        {
            "date": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
            "ticker": ticker,
            "action": action,
            "shares": shares,
            "price": price,
            "realized_pnl": round(realized_pnl, 2) if realized_pnl is not None else None,
        }
    )

    save_portfolio(portfolio_id, state)
    return get_portfolio(portfolio_id)


def reset(portfolio_id: str, starting_capital: float | None = None) -> PortfolioView:
    reset_portfolio(portfolio_id, starting_capital)
    return get_portfolio(portfolio_id)
