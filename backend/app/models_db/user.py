from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.timeutil import utcnow_naive as _utcnow

ROLE_USER = "USER"
ROLE_ADMIN = "ADMIN"


def _uuid_str() -> str:
    return str(uuid.uuid4())



class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    # Argon2id hash string (see app.auth.security) - never a plaintext password,
    # never a manually-implemented hash (e.g. bare SHA-256).
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=ROLE_USER)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Set when a user requests account deletion; the account is disabled
    # immediately and the row is anonymized/removed by the deletion workflow
    # (see app.auth.service.delete_account and docs/AUTHENTICATION.md).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    preferences: Mapped["UserPreferences"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    default_benchmark: Mapped[str] = mapped_column(String(12), nullable=False, default="SPY")
    theme: Mapped[str] = mapped_column(String(20), nullable=False, default="dark")
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    research_notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Terms/privacy acceptance is required at registration; marketing consent
    # is a distinct, separately-opted-in flag - accepting the Terms of
    # Service must never imply marketing consent.
    marketing_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user: Mapped["User"] = relationship(back_populates="preferences")
