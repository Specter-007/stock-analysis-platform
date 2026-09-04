from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.timeutil import utcnow_naive as _utcnow

STATUS_OPEN = "OPEN"
STATUS_CLOSED = "CLOSED"


def _uuid_str() -> str:
    return str(uuid.uuid4())



class SupportRequest(Base):
    __tablename__ = "support_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    # Nullable: the contact form is also reachable by a signed-out visitor.
    # When the requester is authenticated, the row is auto-associated with
    # their account (see app.support.service).
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    contact_email: Mapped[str] = mapped_column(String(320), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_OPEN)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
