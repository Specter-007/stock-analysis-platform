"""Contact/support requests. Reachable by both signed-in and anonymous
visitors; when the requester is authenticated, the ticket is auto-
associated with their account. No email is actually sent unless a real
provider is configured (see app.auth.email) - the confirmation message
returned to the caller reflects that honestly rather than claiming a
message was emailed.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models_db.support import SupportRequest


def create_support_request(
    db: Session, *, user_id: str | None, contact_email: str, category: str, subject: str, message: str
) -> SupportRequest:
    request = SupportRequest(
        user_id=user_id, contact_email=contact_email, category=category, subject=subject, message=message
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def list_my_support_requests(db: Session, user_id: str) -> list[SupportRequest]:
    return list(
        db.query(SupportRequest).filter_by(user_id=user_id).order_by(SupportRequest.created_at.desc()).all()
    )


# --- Admin (see app.auth.dependencies.require_admin - not reachable by normal users) ---

def admin_list_support_requests(db: Session, status: str | None = None, limit: int = 100) -> list[SupportRequest]:
    query = db.query(SupportRequest)
    if status is not None:
        query = query.filter_by(status=status)
    return list(query.order_by(SupportRequest.created_at.desc()).limit(min(limit, 500)).all())


def admin_set_support_request_status(db: Session, request_id: str, status: str) -> SupportRequest | None:
    from app.models_db.support import STATUS_CLOSED, STATUS_OPEN

    if status not in (STATUS_OPEN, STATUS_CLOSED):
        raise ValueError(f"Invalid status: {status!r}")
    request = db.get(SupportRequest, request_id)
    if request is None:
        return None
    request.status = status
    db.commit()
    db.refresh(request)
    return request
