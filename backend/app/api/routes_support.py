from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_current_user
from app.db.base import get_db
from app.models_db.user import User
from app.rate_limit import limiter
from app.settings import EMAIL_PROVIDER, RATE_LIMIT_CONTACT
from app.support import service
from app.support.schemas import ContactRequest, ContactResponse

router = APIRouter(prefix="/api/support", tags=["support"])


@router.post("", response_model=ContactResponse)
@limiter.limit(RATE_LIMIT_CONTACT)
def submit_contact_request(
    request: Request,
    body: ContactRequest,
    user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    created = service.create_support_request(
        db,
        user_id=user.id if user else None,
        contact_email=body.contact_email,
        category=body.category,
        subject=body.subject,
        message=body.message,
    )
    if EMAIL_PROVIDER == "smtp":
        confirmation = "Your message has been received. A confirmation email will be sent shortly."
    else:
        confirmation = (
            "Your message has been received and stored. No confirmation email was sent - this "
            "deployment does not have a real email provider configured (EMAIL_PROVIDER=console)."
        )
    return ContactResponse(id=created.id, created_at=created.created_at, message=confirmation)
