from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Query

from app.config import MOVERS_WATCHLIST
from app.models.schemas import IndexQuote, MarketOverviewResponse, MoverQuote, SearchResponse, SearchResultItem
from app.services import market_data

router = APIRouter(prefix="/api", tags=["market"])


@router.get("/market/status", response_model=MarketOverviewResponse)
def get_market_status():
    with ThreadPoolExecutor(max_workers=2) as pool:
        indexes_future = pool.submit(market_data.get_market_indexes)
        movers_future = pool.submit(market_data.get_movers, MOVERS_WATCHLIST)
        indexes, index_meta = indexes_future.result()
        movers, movers_meta = movers_future.result()

    ranked = sorted(movers, key=lambda m: m["change_percent"], reverse=True)
    gainers = [m for m in ranked if m["change_percent"] > 0][:5]
    losers = sorted([m for m in ranked if m["change_percent"] < 0], key=lambda m: m["change_percent"])[:5]

    return MarketOverviewResponse(
        indexes=[IndexQuote(**i) for i in indexes],
        gainers=[MoverQuote(**g) for g in gainers],
        losers=[MoverQuote(**l) for l in losers],
        meta=index_meta.to_dict(),
    )


@router.get("/search", response_model=SearchResponse)
def search_tickers(q: str = Query(..., min_length=1, max_length=64)):
    results = market_data.search_symbols(q)
    from app.services.market_data import DataMeta

    meta = DataMeta(data_status="HISTORICAL", timeframe="N/A")
    return SearchResponse(
        query=q,
        results=[SearchResultItem(**r) for r in results],
        meta=meta.to_dict(),
    )
