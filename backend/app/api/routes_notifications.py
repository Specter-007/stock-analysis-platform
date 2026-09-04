from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_csrf
from app.auth.exceptions import ResourceNotFoundError
from app.db.base import get_db
from app.models_db.user import User
from app.notifications import service
from app.notifications.schemas import (
    MarkReadResponse,
    NotificationListResponse,
    NotificationModel,
    UnreadCountResponse,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=service.DEFAULT_LIST_LIMIT, le=service.MAX_LIST_LIMIT),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifications = service.list_notifications(db, user.id, unread_only=unread_only, limit=limit)
    return NotificationListResponse(
        notifications=[NotificationModel(**{k: getattr(n, k) for k in NotificationModel.model_fields}) for n in notifications],
        unread_count=service.unread_count(db, user.id),
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UnreadCountResponse(unread_count=service.unread_count(db, user.id))


@router.post("/{notification_id}/read", response_model=MarkReadResponse)
def mark_notification_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    _csrf: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    if not service.mark_read(db, user.id, notification_id):
        raise ResourceNotFoundError("Notification not found.")
    return MarkReadResponse(marked=1)


@router.post("/read-all", response_model=MarkReadResponse)
def mark_all_notifications_read(
    user: User = Depends(get_current_user), _csrf: User = Depends(require_csrf), db: Session = Depends(get_db)
):
    count = service.mark_all_read(db, user.id)
    return MarkReadResponse(marked=count)
