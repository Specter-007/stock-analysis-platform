from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import portable_json



class ExperimentDB(Base):
    __tablename__ = "experiments"

    # Kept as the existing "exp_" + 12 hex chars format (app.experiments.store)
    # rather than a fresh UUID, since it is already embedded in fingerprints,
    # forward-simulation portfolio links, and exported JSON files.
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(portable_json(), nullable=False)
    results: Mapped[dict] = mapped_column(portable_json(), nullable=False)
    data_provenance: Mapped[dict | None] = mapped_column(portable_json(), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list] = mapped_column(portable_json(), nullable=False, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    forward_portfolio_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reproduced_from: Mapped[str | None] = mapped_column(String(40), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Stored as the same ISO-8601 UTC string app.experiments.service already
    # computes (app.utils.timeutils.to_iso) - avoids a redundant datetime<->
    # string conversion layer since the service, not the DB, owns these
    # timestamps (e.g. updated_at changes on notes/status edits, not only on
    # row writes).
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False)
