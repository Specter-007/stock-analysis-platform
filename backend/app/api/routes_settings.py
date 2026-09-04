from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_csrf
from app.data_export.service import export_user_data
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


@router.get("/export")
def export_my_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Structured JSON export of everything this endpoint's caller owns -
    profile, preferences, watchlists, paper portfolios (incl. trades and
    equity snapshots), experiments, notifications, and support requests.
    Never includes the password hash, session/CSRF/reset-token secrets, or
    any other user's data. Providing this export does not by itself imply
    GDPR/KVKK compliance - see docs/SECURITY.md.
    """
    payload = export_user_data(db, user)
    body = json.dumps(payload, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="account-export-{user.id}.json"'},
    )
