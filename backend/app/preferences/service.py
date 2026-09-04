from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.timeutil import utcnow_naive
from app.models_db.user import UserPreferences


def get_preferences(db: Session, user_id: str) -> UserPreferences:
    prefs = db.get(UserPreferences, user_id)
    if prefs is None:
        # Defensive fallback only - every user gets a UserPreferences row at
        # registration (see app.auth.service.register); this path exists so
        # a pre-migration legacy account is never left without one.
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def update_preferences(db: Session, user_id: str, **fields) -> UserPreferences:
    prefs = get_preferences(db, user_id)
    for key, value in fields.items():
        if value is not None:
            setattr(prefs, key, value)
    db.commit()
    db.refresh(prefs)
    return prefs


def complete_onboarding(db: Session, user_id: str) -> UserPreferences:
    prefs = get_preferences(db, user_id)
    if not prefs.onboarding_completed:
        prefs.onboarding_completed = True
        prefs.onboarding_completed_at = utcnow_naive()
        db.commit()
        db.refresh(prefs)
    return prefs
