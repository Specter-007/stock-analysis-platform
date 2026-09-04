"""Notifications: created ONLY from real backend events (see call sites in
app.experiments.service and app.paper_trading.service) - there is no path
in this codebase that creates a notification for demonstration or
marketing purposes.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.timeutil import utcnow_naive
from app.models_db.notification import Notification

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200


def create_notification(
    db: Session, user_id: str, type_: str, title: str, message: str, target_route: str | None = None
) -> Notification:
    notification = Notification(user_id=user_id, type=type_, title=title, message=message, target_route=target_route)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_notifications(db: Session, user_id: str, unread_only: bool = False, limit: int = DEFAULT_LIST_LIMIT) -> list[Notification]:
    limit = max(1, min(limit, MAX_LIST_LIMIT))
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    return list(db.scalars(query))


def unread_count(db: Session, user_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
    ) or 0


def mark_read(db: Session, user_id: str, notification_id: str) -> bool:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        return False
    if notification.read_at is None:
        notification.read_at = utcnow_naive()
        db.commit()
    return True


def mark_all_read(db: Session, user_id: str) -> int:
    notifications = db.scalars(
        select(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
    ).all()
    now = utcnow_naive()
    for n in notifications:
        n.read_at = now
    db.commit()
    return len(notifications)
