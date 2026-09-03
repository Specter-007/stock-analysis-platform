"""Sector peer comparison.

`SECTOR_PEER_MAP` (in `app.config`) only decides WHICH tickers are
compared for a given sector - it is a curated list of large, liquid
representative names, not financial data. Every return shown is computed
from real historical prices fetched live via yfinance.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.config import SECTOR_PEER_DISPLAY_COUNT, SECTOR_PEER_MAP
from app.market.relative_strength import period_return
from app.services import market_data

logger = logging.getLogger(__name__)

SECTOR_COMPARISON_PERIOD_LABEL = "3M"
SECTOR_COMPARISON_PERIOD_SESSIONS = 63


@dataclass
class SectorPeerReturn:
    symbol: str
    return_percent: float | None


@dataclass
class SectorComparisonResult:
    sector: str | None
    period: str
    ticker: str
    peers: list[SectorPeerReturn]
    available: bool


def _fetch_peer_return(symbol: str) -> SectorPeerReturn:
    try:
        df = market_data.fetch_history_raw(symbol, "6mo", "1d")
        if df is None or df.empty:
            return SectorPeerReturn(symbol=symbol, return_percent=None)
        ret = period_return(df["Close"], SECTOR_COMPARISON_PERIOD_SESSIONS)
        return SectorPeerReturn(symbol=symbol, return_percent=round(ret, 2) if ret is not None else None)
    except Exception as exc:
        logger.warning("Failed to fetch sector peer %s: %s", symbol, exc)
        return SectorPeerReturn(symbol=symbol, return_percent=None)


def compare_sector(ticker: str, sector: str | None) -> SectorComparisonResult:
    if not sector or sector == "N/A" or sector not in SECTOR_PEER_MAP:
        return SectorComparisonResult(
            sector=sector, period=SECTOR_COMPARISON_PERIOD_LABEL, ticker=ticker, peers=[], available=False
        )

    peer_symbols = [p for p in SECTOR_PEER_MAP[sector] if p != ticker][:SECTOR_PEER_DISPLAY_COUNT]
    symbols_to_fetch = [ticker] + peer_symbols

    with ThreadPoolExecutor(max_workers=min(8, len(symbols_to_fetch))) as pool:
        results = list(pool.map(_fetch_peer_return, symbols_to_fetch))

    ranked = sorted(results, key=lambda r: (r.return_percent is None, -(r.return_percent or 0)))

    return SectorComparisonResult(
        sector=sector,
        period=SECTOR_COMPARISON_PERIOD_LABEL,
        ticker=ticker,
        peers=ranked,
        available=any(r.return_percent is not None for r in results),
    )
