"""PostgreSQL-backed (SQLAlchemy) watchlist persistence, scoped per user.

Replaces the earlier JSON-file store (see docs/MIGRATION.md for the
one-time import of any pre-existing single-user JSON watchlist data). The
`watchlist_id` a caller supplies is treated as a "slug" - a client-chosen
name (e.g. "default") - and is always looked up together with the
authenticated user's id, so two different users can each have their own
"default" watchlist without collision, and neither can ever read or write
the other's by guessing/choosing the same slug.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models_db.watchlist import WatchlistDB

DEFAULT_WATCHLIST_ID = "default"
_MAX_SLUG_LENGTH = 64


def _sanitize_slug(watchlist_id: str) -> str:
    safe = "".join(c for c in watchlist_id if c.isalnum() or c in ("-", "_")) or DEFAULT_WATCHLIST_ID
    return safe[:_MAX_SLUG_LENGTH]


def _get_row(db: Session, user_id: str, watchlist_id: str) -> WatchlistDB | None:
    slug = _sanitize_slug(watchlist_id)
    return db.query(WatchlistDB).filter_by(user_id=user_id, slug=slug).one_or_none()


def load_tickers(db: Session, user_id: str, watchlist_id: str = DEFAULT_WATCHLIST_ID) -> list[str]:
    row = _get_row(db, user_id, watchlist_id)
    return list(row.tickers) if row is not None else []


def save_tickers(db: Session, user_id: str, watchlist_id: str, tickers: list[str]) -> None:
    row = _get_row(db, user_id, watchlist_id)
    if row is None:
        db.add(WatchlistDB(user_id=user_id, slug=_sanitize_slug(watchlist_id), tickers=list(tickers)))
    else:
        row.tickers = list(tickers)
    db.commit()


def list_watchlist_slugs(db: Session, user_id: str) -> list[str]:
    rows = db.query(WatchlistDB.slug).filter_by(user_id=user_id).order_by(WatchlistDB.slug).all()
    return [r[0] for r in rows]


def list_all_watchlists(db: Session, user_id: str) -> list[WatchlistDB]:
    """Full rows (not just slugs) - used by the account data-export endpoint."""
    return list(db.query(WatchlistDB).filter_by(user_id=user_id).order_by(WatchlistDB.slug).all())
