from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class NotificationModel(BaseModel):
    id: str
    type: str
    title: str
    message: str
    target_route: str | None
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationModel]
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    marked: int
