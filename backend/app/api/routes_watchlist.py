from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_csrf
from app.db.base import get_db
from app.models.schemas import WatchlistAddRequest, WatchlistEntryModel, WatchlistResponse
from app.models_db.user import User
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
def get_watchlist(
    watchlist_id: str = Query(default=DEFAULT_WATCHLIST_ID),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = watchlist_service.get_watchlist(db, user.id, watchlist_id)
    return _to_response(result)


@router.post("", response_model=WatchlistResponse)
def add_to_watchlist(
    request: WatchlistAddRequest,
    user: User = Depends(get_current_user),
    _csrf: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    watchlist_service.add_ticker(db, user.id, request.watchlist_id, request.ticker)
    result = watchlist_service.get_watchlist(db, user.id, request.watchlist_id)
    return _to_response(result)


@router.delete("/{ticker}", response_model=WatchlistResponse)
def remove_from_watchlist(
    ticker: str,
    watchlist_id: str = Query(default=DEFAULT_WATCHLIST_ID),
    user: User = Depends(get_current_user),
    _csrf: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    watchlist_service.remove_ticker(db, user.id, watchlist_id, ticker)
    result = watchlist_service.get_watchlist(db, user.id, watchlist_id)
    return _to_response(result)
