from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PURPOSE_PASSWORD_RESET = "PASSWORD_RESET"
PURPOSE_EMAIL_VERIFY = "EMAIL_VERIFY"
PURPOSE_EMAIL_CHANGE = "EMAIL_CHANGE"


def _uuid_str() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthToken(Base):
    """A single-use, expiring, secret token for password reset, email
    verification, or email change. Only the SHA-256 hash of the raw token
    is stored; the raw token is emailed to the user and never persisted.
    """

    __tablename__ = "auth_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # Only populated for PURPOSE_EMAIL_CHANGE - the new address is not
    # applied to the user record until this token is verified.
    new_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
