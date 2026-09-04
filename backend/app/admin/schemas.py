from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AdminUserModel(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login_at: datetime | None


class AdminUserListResponse(BaseModel):
    users: list[AdminUserModel]


class AdminSupportRequestModel(BaseModel):
    id: str
    user_id: str | None
    contact_email: str
    category: str
    subject: str
    message: str
    status: str
    created_at: datetime


class AdminSupportRequestListResponse(BaseModel):
    requests: list[AdminSupportRequestModel]


class UpdateSupportRequestStatusRequest(BaseModel):
    status: str


class SetUserActiveRequest(BaseModel):
    is_active: bool
