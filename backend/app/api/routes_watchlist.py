from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.schemas import WatchlistAddRequest, WatchlistEntryModel, WatchlistResponse
from app.watchlist import service as watchlist_service
from app.watchlist.store import DEFAULT_WATCHLIST_ID

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def _to_response(result) -> WatchlistResponse:
    return WatchlistResponse(
        watchlist_id=result.watchlist_id,
        tickers=result.tickers,
        entries=[WatchlistEntryModel(**e.__dict__) for e in result.entries],
    )


@router.get("", response_model=WatchlistResponse)
def get_watchlist(watchlist_id: str = Query(default=DEFAULT_WATCHLIST_ID)):
    result = watchlist_service.get_watchlist(watchlist_id)
    return _to_response(result)


@router.post("", response_model=WatchlistResponse)
def add_to_watchlist(request: WatchlistAddRequest):
    watchlist_service.add_ticker(request.watchlist_id, request.ticker)
    result = watchlist_service.get_watchlist(request.watchlist_id)
    return _to_response(result)


@router.delete("/{ticker}", response_model=WatchlistResponse)
def remove_from_watchlist(ticker: str, watchlist_id: str = Query(default=DEFAULT_WATCHLIST_ID)):
    watchlist_service.remove_ticker(watchlist_id, ticker)
    result = watchlist_service.get_watchlist(watchlist_id)
    return _to_response(result)
