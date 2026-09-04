from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_csrf
from app.db.base import get_db
from app.models_db.user import User
from app.preferences import service
from app.preferences.schemas import PreferencesResponse, UpdatePreferencesRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_response(prefs) -> PreferencesResponse:
    return PreferencesResponse(
        timezone=prefs.timezone,
        default_benchmark=prefs.default_benchmark,
        theme=prefs.theme,
        email_notifications_enabled=prefs.email_notifications_enabled,
        research_notifications_enabled=prefs.research_notifications_enabled,
        marketing_consent=prefs.marketing_consent,
        terms_accepted_at=prefs.terms_accepted_at,
        privacy_accepted_at=prefs.privacy_accepted_at,
        onboarding_completed=prefs.onboarding_completed,
        onboarding_completed_at=prefs.onboarding_completed_at,
    )


@router.get("/preferences", response_model=PreferencesResponse)
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _to_response(service.get_preferences(db, user.id))


@router.patch("/preferences", response_model=PreferencesResponse)
def update_preferences(
    request: UpdatePreferencesRequest,
    user: User = Depends(get_current_user),
    _csrf: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    prefs = service.update_preferences(db, user.id, **request.model_dump())
    return _to_response(prefs)


@router.post("/onboarding/complete", response_model=PreferencesResponse)
def complete_onboarding(
    user: User = Depends(get_current_user), _csrf: User = Depends(require_csrf), db: Session = Depends(get_db)
):
    prefs = service.complete_onboarding(db, user.id)
    return _to_response(prefs)
