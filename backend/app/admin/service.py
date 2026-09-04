"""Minimal admin operations - backend-enforced (app.auth.dependencies.
require_admin), never exposed to normal users. Deliberately small: basic
user/account status and support-ticket triage only, not a general admin
dashboard.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models_db.user import User


def list_users(db: Session, limit: int = 200) -> list[User]:
    return list(db.query(User).order_by(User.created_at.desc()).limit(min(limit, 500)).all())


def set_user_active(db: Session, user_id: str, is_active: bool) -> User | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user
