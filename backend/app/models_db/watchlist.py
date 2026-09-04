from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.timeutil import utcnow_naive as _utcnow
from app.db.types import portable_json


def _uuid_str() -> str:
    return str(uuid.uuid4())



class WatchlistDB(Base):
    __tablename__ = "watchlists"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_watchlist_user_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Client-chosen name (e.g. "default"), unique per-user - lets two users
    # each keep their own "default" watchlist without collision.
    slug: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    tickers: Mapped[list] = mapped_column(portable_json(), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )
