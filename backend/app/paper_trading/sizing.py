"""Position-sizing rules for paper trading. Long-only, no leverage: every
mode below can only ever return a share count whose cost is covered by
available cash - it is mathematically impossible for these functions to
produce a negative cash balance on their own (the caller still re-checks
cash before executing, as the final backstop).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import PAPER_TRADING_DEFAULT_MAX_POSITION_PERCENT

SIZING_MODES = ("FIXED_SHARES", "FIXED_CAPITAL_PERCENT", "RISK_PERCENT")


class PositionSizingError(ValueError):
    pass


@dataclass
class SizingRequest:
    mode: str
    price: float
    portfolio_equity: float
    available_cash: float
    shares: float | None = None  # FIXED_SHARES
    capital_percent: float | None = None  # FIXED_CAPITAL_PERCENT: % of equity to allocate
    risk_percent: float | None = None  # RISK_PERCENT: % of equity willing to lose
    stop_loss_percent: float | None = None  # RISK_PERCENT requires this to size against
    max_position_percent: float = PAPER_TRADING_DEFAULT_MAX_POSITION_PERCENT


def calculate_shares(request: SizingRequest) -> float:
    if request.mode not in SIZING_MODES:
        raise PositionSizingError(f"Unknown position sizing mode '{request.mode}'.")
    if request.price <= 0:
        raise PositionSizingError("Price must be positive to size a position.")

    if request.mode == "FIXED_SHARES":
        if not request.shares or request.shares <= 0:
            raise PositionSizingError("FIXED_SHARES sizing requires a positive 'shares' value.")
        shares = request.shares

    elif request.mode == "FIXED_CAPITAL_PERCENT":
        if not request.capital_percent or request.capital_percent <= 0:
            raise PositionSizingError("FIXED_CAPITAL_PERCENT sizing requires a positive 'capital_percent'.")
        allocation = request.portfolio_equity * (request.capital_percent / 100.0)
        shares = allocation / request.price

    else:  # RISK_PERCENT
        if not request.risk_percent or request.risk_percent <= 0:
            raise PositionSizingError("RISK_PERCENT sizing requires a positive 'risk_percent'.")
        if not request.stop_loss_percent or request.stop_loss_percent <= 0:
            raise PositionSizingError(
                "RISK_PERCENT sizing requires a positive 'stop_loss_percent' to size against "
                "(the position is sized so that a stop-loss hit loses exactly risk_percent of equity)."
            )
        risk_amount = request.portfolio_equity * (request.risk_percent / 100.0)
        per_share_risk = request.price * (request.stop_loss_percent / 100.0)
        shares = risk_amount / per_share_risk

    # Hard caps: never exceed the max-position-percent backstop, and never
    # exceed what available cash can actually cover.
    max_notional = request.portfolio_equity * (request.max_position_percent / 100.0)
    shares = min(shares, max_notional / request.price)
    shares = min(shares, request.available_cash / request.price)

    if shares <= 0:
        raise PositionSizingError("Calculated position size is zero or negative (insufficient cash or equity).")

    return shares
