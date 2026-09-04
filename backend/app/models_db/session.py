from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.timeutil import utcnow_naive as _utcnow


def _uuid_str() -> str:
    return str(uuid.uuid4())



class UserSession(Base):
    """A server-tracked login session, referenced by an httpOnly session
    cookie. The cookie carries a high-entropy opaque token; only its SHA-256
    hash is ever persisted, so a database read alone cannot be used to
    impersonate a user (mirrors how passwords/reset tokens are stored).
    """

    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Stored only for the user's own "active sessions" security view (e.g.
    # "Chrome on Windows"); truncated, never used for fingerprinting/tracking.
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # IP address is optional/nullable and only recorded to help a user
    # recognize a suspicious session in their own security settings - not
    # used for analytics or shared with any third party.
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
