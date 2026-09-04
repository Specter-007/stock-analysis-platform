from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin import service as admin_service
from app.admin.schemas import (
    AdminSupportRequestListResponse,
    AdminSupportRequestModel,
    AdminUserListResponse,
    AdminUserModel,
    SetUserActiveRequest,
    UpdateSupportRequestStatusRequest,
)
from app.auth.dependencies import require_admin, require_csrf
from app.auth.exceptions import ResourceNotFoundError
from app.db.base import get_db
from app.models_db.user import User
from app.support import service as support_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserListResponse)
def list_users(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = admin_service.list_users(db)
    return AdminUserListResponse(users=[AdminUserModel.model_validate(u, from_attributes=True) for u in users])


@router.post("/users/{user_id}/active", response_model=AdminUserModel)
def set_user_active(
    user_id: str,
    body: SetUserActiveRequest,
    _admin: User = Depends(require_admin),
    _csrf: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    updated = admin_service.set_user_active(db, user_id, body.is_active)
    if updated is None:
        raise ResourceNotFoundError("User not found.")
    return AdminUserModel.model_validate(updated, from_attributes=True)


@router.get("/support-requests", response_model=AdminSupportRequestListResponse)
def list_support_requests(
    status: str | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    requests = support_service.admin_list_support_requests(db, status=status)
    return AdminSupportRequestListResponse(
        requests=[AdminSupportRequestModel.model_validate(r, from_attributes=True) for r in requests]
    )


@router.patch("/support-requests/{request_id}", response_model=AdminSupportRequestModel)
def update_support_request_status(
    request_id: str,
    body: UpdateSupportRequestStatusRequest,
    _admin: User = Depends(require_admin),
    _csrf: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    try:
        updated = support_service.admin_set_support_request_status(db, request_id, body.status)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise ResourceNotFoundError("Support request not found.")
    return AdminSupportRequestModel.model_validate(updated, from_attributes=True)
