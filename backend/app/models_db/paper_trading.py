from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import portable_json


def _uuid_str() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaperPortfolioDB(Base):
    __tablename__ = "paper_portfolios"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_portfolio_user_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    # The entire existing paper-trading state dict (cash, positions, trades,
    # equity_snapshots, benchmark_basis, ...) exactly as previously written
    # to data/paper_trading/<id>.json - preserved byte-for-shape so the
    # unchanged app.paper_trading.service logic can keep operating on it.
    state: Mapped[dict] = mapped_column(portable_json(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
