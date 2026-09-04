"""PostgreSQL-backed (SQLAlchemy) persistence for paper-trading portfolios,
scoped per user.

Replaces the earlier JSON-file store (see docs/MIGRATION.md for the
one-time import of any pre-existing single-user JSON portfolio data). The
entire state dict shape is unchanged - it is simply the JSON payload of a
PaperPortfolioDB.state column now instead of a `<id>.json` file - so the
math/business logic in app.paper_trading.service (position sizing, cost
accounting, equity snapshots) is untouched. `portfolio_id` is treated as a
"slug" (e.g. "default") looked up together with the authenticated user's
id, so two users can each have their own "default" portfolio.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import PAPER_TRADING_DEFAULT_CAPITAL
from app.models_db.paper_trading import PaperPortfolioDB

_MAX_SLUG_LENGTH = 64


def _sanitize_slug(portfolio_id: str) -> str:
    safe = "".join(c for c in portfolio_id if c.isalnum() or c in ("-", "_")) or "default"
    return safe[:_MAX_SLUG_LENGTH]


def _default_state(portfolio_id: str) -> dict:
    return {
        "portfolio_id": portfolio_id,
        "starting_capital": PAPER_TRADING_DEFAULT_CAPITAL,
        "cash": PAPER_TRADING_DEFAULT_CAPITAL,
        "positions": {},  # ticker -> {"shares": float, "avg_entry_price": float}
        "trades": [],  # list of trade dicts, oldest first
        # Append-only forward-validation equity curve - one entry per real
        # trading day the portfolio was actually observed on, never one per
        # calendar day (weekends/holidays are never fabricated). See
        # app.paper_trading.service._maybe_record_snapshot.
        "equity_snapshots": [],
        # Fixes the SPY price/date the benchmark curve is indexed from - set
        # once, on this portfolio's first-ever snapshot, so "started with the
        # same capital on the same day" holds for the life of the portfolio.
        "benchmark_basis": None,
    }


def _get_row(db: Session, user_id: str, portfolio_id: str, *, for_update: bool = False) -> PaperPortfolioDB | None:
    slug = _sanitize_slug(portfolio_id)
    query = db.query(PaperPortfolioDB).filter_by(user_id=user_id, slug=slug)
    if for_update:
        # Row-level lock (SELECT ... FOR UPDATE on PostgreSQL; a documented
        # no-op on SQLite, which serializes writes at the whole-database
        # level instead - safe either way). Held until this transaction
        # commits (i.e. until the paired save_portfolio() call below), so a
        # second concurrent read-modify-write cycle for the SAME row blocks
        # until the first one finishes, then sees its committed result -
        # closing the equity-snapshot/trade race documented in
        # docs/SECURITY.md without any schema change. Only used by callers
        # that are about to save_portfolio() afterward - a pure read (e.g.
        # get_equity_history's display read) must not lock.
        query = query.with_for_update()
    return query.one_or_none()


def load_portfolio(db: Session, user_id: str, portfolio_id: str, *, for_update: bool = False) -> dict:
    row = _get_row(db, user_id, portfolio_id, for_update=for_update)
    return dict(row.state) if row is not None else _default_state(portfolio_id)


def save_portfolio(db: Session, user_id: str, portfolio_id: str, state: dict) -> None:
    row = _get_row(db, user_id, portfolio_id)
    if row is None:
        db.add(PaperPortfolioDB(user_id=user_id, slug=_sanitize_slug(portfolio_id), state=dict(state)))
    else:
        row.state = dict(state)
    db.commit()


def reset_portfolio(db: Session, user_id: str, portfolio_id: str, starting_capital: float | None = None) -> dict:
    state = _default_state(portfolio_id)
    if starting_capital is not None:
        state["starting_capital"] = starting_capital
        state["cash"] = starting_capital
    save_portfolio(db, user_id, portfolio_id, state)
    return state


def list_portfolio_ids(db: Session, user_id: str) -> list[str]:
    """Every portfolio slug this user has ever saved - the DB rows scoped to
    this user ARE the index, mirroring the old JSON-directory-listing
    approach (see the V5 changelog) but now naturally per-user."""
    rows = db.query(PaperPortfolioDB.slug).filter_by(user_id=user_id).order_by(PaperPortfolioDB.slug).all()
    return [r[0] for r in rows]


def list_all_portfolios(db: Session, user_id: str) -> list[PaperPortfolioDB]:
    """Full rows (not just slugs) - used by the account data-export endpoint."""
    return list(db.query(PaperPortfolioDB).filter_by(user_id=user_id).order_by(PaperPortfolioDB.slug).all())
