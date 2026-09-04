from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.timeutil import utcnow_naive as _utcnow

# Every notification type corresponds to a real, already-occurring backend
# event - see app.notifications.service. There is no path in this codebase
# that creates a notification for demonstration/marketing purposes.
TYPE_EXPERIMENT_COMPLETED = "EXPERIMENT_COMPLETED"
TYPE_EXPERIMENT_FAILED = "EXPERIMENT_FAILED"
TYPE_PAPER_PORTFOLIO_EVENT = "PAPER_PORTFOLIO_EVENT"
TYPE_SYSTEM = "SYSTEM"


def _uuid_str() -> str:
    return str(uuid.uuid4())



class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_route: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
