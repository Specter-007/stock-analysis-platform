"""Paper-portfolio risk dashboard.

Scope note: computing true portfolio-level volatility, Sharpe/Sortino, beta,
and drawdown would require a persisted daily equity-curve time series, which
this lightweight JSON-ledger paper-trading store does not keep (it stores
trades and current positions, not a daily snapshot history). Rather than
approximate those with a method that isn't actually measuring what it claims
to measure, this module reports what CAN be computed correctly from the
portfolio's current, real state: exposure, cash, concentration (by position
and by sector), and threshold-based warnings - and documents the omission
rather than filling the gap with a fabricated number.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.services import market_data


@dataclass
class PaperRiskResult:
    total_exposure_percent: float
    cash_percent: float
    largest_position_percent: float
    number_of_positions: int
    sector_concentration: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    methodology: str = (
        "Exposure, cash %, and position/sector concentration are computed directly from the "
        "portfolio's current real positions and live quotes. Portfolio-level volatility, Sharpe, "
        "Sortino, beta, and historical drawdown are NOT included here: they require a persisted "
        "daily equity-curve history that this lightweight paper-trading ledger does not keep. "
        "This is a documented scope limit, not an approximation standing in for those metrics."
    )


HIGH_CONCENTRATION_THRESHOLD = 40.0
LOW_CASH_THRESHOLD = 5.0
HIGH_DRAWDOWN_THRESHOLD = -20.0
HIGH_SECTOR_CONCENTRATION_THRESHOLD = 60.0


def _sector_for(ticker: str) -> str:
    try:
        overview, _ = market_data.get_overview(ticker)
        return overview.get("sector") or "Unknown"
    except Exception:
        return "Unknown"


def assess_portfolio_risk(portfolio_view) -> PaperRiskResult:
    warnings: list[str] = []

    if portfolio_view.largest_position_percent >= HIGH_CONCENTRATION_THRESHOLD:
        warnings.append(
            f"HIGH_CONCENTRATION: largest position is {portfolio_view.largest_position_percent:.1f}% of portfolio value."
        )
    if portfolio_view.cash_percent <= LOW_CASH_THRESHOLD and portfolio_view.number_of_positions > 0:
        warnings.append(f"LOW_CASH: only {portfolio_view.cash_percent:.1f}% of the portfolio is in cash.")
    if portfolio_view.total_return_percent <= HIGH_DRAWDOWN_THRESHOLD:
        warnings.append(f"HIGH_DRAWDOWN: portfolio is down {portfolio_view.total_return_percent:.1f}% from starting capital.")

    sector_value: dict[str, float] = {}
    if portfolio_view.positions:
        tickers = [p.ticker for p in portfolio_view.positions]
        with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as pool:
            sectors = list(pool.map(_sector_for, tickers))
        for p, sector in zip(portfolio_view.positions, sectors):
            if p.market_value:
                sector_value[sector] = sector_value.get(sector, 0.0) + p.market_value

    total_position_value = sum(sector_value.values())
    sector_concentration = {
        s: round(v / total_position_value * 100.0, 1) for s, v in sector_value.items()
    } if total_position_value > 0 else {}

    if sector_concentration:
        top_sector, top_pct = max(sector_concentration.items(), key=lambda kv: kv[1])
        if top_pct >= HIGH_SECTOR_CONCENTRATION_THRESHOLD:
            warnings.append(f"HIGH_CONCENTRATION: {top_pct:.1f}% of holdings are in {top_sector}.")

    return PaperRiskResult(
        total_exposure_percent=portfolio_view.exposure_percent,
        cash_percent=portfolio_view.cash_percent,
        largest_position_percent=portfolio_view.largest_position_percent,
        number_of_positions=portfolio_view.number_of_positions,
        sector_concentration=sector_concentration,
        warnings=warnings,
    )
