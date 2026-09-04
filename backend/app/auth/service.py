"""Auth business logic: registration, login/logout, session lifecycle,
password reset, email verification, email change, account deletion.

Every function takes an explicit SQLAlchemy `Session` (the request-scoped
`db` from app.db.base.get_db) - no module-level DB state.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.email import send_email
from app.auth.exceptions import (
    AccountNotActiveError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
)
from app.auth.security import (
    generate_opaque_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.models_db.tokens import (
    PURPOSE_EMAIL_CHANGE,
    PURPOSE_EMAIL_VERIFY,
    PURPOSE_PASSWORD_RESET,
    AuthToken,
)
from app.db.timeutil import utcnow_naive as _utcnow
from app.models_db.session import UserSession
from app.models_db.user import User, UserPreferences
from app.settings import FRONTEND_URL, SESSION_TTL_DAYS

logger = logging.getLogger(__name__)

PASSWORD_RESET_TOKEN_TTL = timedelta(hours=1)
EMAIL_VERIFY_TOKEN_TTL = timedelta(hours=24)
EMAIL_CHANGE_TOKEN_TTL = timedelta(hours=1)

# Truncated in the DB - only used for a human-readable "active sessions" list.
_MAX_USER_AGENT_LENGTH = 255


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == _normalize_email(email)))


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def register(db: Session, *, email: str, password: str, display_name: str) -> User:
    email = _normalize_email(email)
    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError("An account with this email already exists.")

    user = User(email=email, password_hash=hash_password(password), display_name=display_name)
    db.add(user)
    db.flush()  # populate user.id before creating the dependent row
    db.add(UserPreferences(user_id=user.id))
    db.commit()
    db.refresh(user)
    logger.info("New account registered: user_id=%s", user.id)
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    """Raises InvalidCredentialsError with an identical message whether the
    email is unknown, the password is wrong, or the account is inactive -
    never lets a caller distinguish these cases."""
    user = get_user_by_email(db, email)
    generic_error = InvalidCredentialsError("Incorrect email or password.")

    if user is None:
        # Still run a hash verification against a dummy hash so the response
        # time doesn't reveal whether the email exists (timing side-channel).
        verify_password(password, hash_password("dummy-timing-equalizer-password"))
        raise generic_error

    if not verify_password(password, user.password_hash):
        raise generic_error
    if not user.is_active:
        raise generic_error

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.last_login_at = _utcnow()
    db.commit()
    db.refresh(user)
    return user


# --- Sessions ---

def create_session(db: Session, user: User, *, user_agent: str | None, ip_address: str | None) -> tuple[UserSession, str]:
    raw_token = generate_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=_utcnow() + timedelta(days=SESSION_TTL_DAYS),
        user_agent=(user_agent or "")[:_MAX_USER_AGENT_LENGTH] or None,
        ip_address=ip_address,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, raw_token


def get_user_by_session_token(db: Session, raw_token: str) -> tuple[User, UserSession] | None:
    token_hash = hash_token(raw_token)
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if session is None:
        return None
    if session.revoked_at is not None:
        return None
    if session.expires_at <= _utcnow():
        return None
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    return user, session


def touch_session(db: Session, session: UserSession) -> None:
    session.last_seen_at = _utcnow()
    db.commit()


def list_sessions(db: Session, user: User) -> list[UserSession]:
    return list(
        db.scalars(
            select(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.last_seen_at.desc())
        )
    )


def revoke_session(db: Session, user: User, session_id: str) -> bool:
    """Returns False (never raises) if the session doesn't exist or belongs
    to a different user - callers map that to a 404, same as any other
    ownership check in this codebase."""
    session = db.get(UserSession, session_id)
    if session is None or session.user_id != user.id:
        return False
    session.revoked_at = _utcnow()
    db.commit()
    return True


def revoke_all_other_sessions(db: Session, user: User, current_session_id: str) -> int:
    sessions = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.id != current_session_id,
            UserSession.revoked_at.is_(None),
        )
    ).all()
    for session in sessions:
        session.revoked_at = _utcnow()
    db.commit()
    return len(sessions)


def revoke_all_sessions(db: Session, user: User) -> None:
    sessions = db.scalars(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    ).all()
    for session in sessions:
        session.revoked_at = _utcnow()
    db.commit()


# --- Tokens (password reset / email verify / email change) ---

def _issue_token(db: Session, user: User, purpose: str, ttl: timedelta, new_email: str | None = None) -> str:
    raw_token = generate_opaque_token()
    db.add(
        AuthToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(raw_token),
            new_email=new_email,
            expires_at=_utcnow() + ttl,
        )
    )
    db.commit()
    return raw_token


def _consume_token(db: Session, raw_token: str, purpose: str) -> AuthToken:
    token_hash = hash_token(raw_token)
    token = db.scalar(
        select(AuthToken).where(AuthToken.token_hash == token_hash, AuthToken.purpose == purpose)
    )
    if token is None or token.used_at is not None or token.expires_at <= _utcnow():
        raise InvalidOrExpiredTokenError("This link is invalid or has expired. Please request a new one.")
    token.used_at = _utcnow()
    db.commit()
    return token


def request_password_reset(db: Session, email: str) -> None:
    """Always succeeds from the caller's point of view - never reveals
    whether the email is registered (see app.api.routes_auth)."""
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return
    raw_token = _issue_token(db, user, PURPOSE_PASSWORD_RESET, PASSWORD_RESET_TOKEN_TTL)
    link = f"{FRONTEND_URL}/reset-password?token={raw_token}"
    send_email(
        user.email,
        "Reset your password",
        f"Use this link to reset your password (expires in 1 hour):\n{link}\n\n"
        "If you did not request this, you can safely ignore this email.",
    )


def reset_password(db: Session, raw_token: str, new_password: str) -> None:
    token = _consume_token(db, raw_token, PURPOSE_PASSWORD_RESET)
    user = db.get(User, token.user_id)
    if user is None:
        raise InvalidOrExpiredTokenError("This link is invalid or has expired. Please request a new one.")
    user.password_hash = hash_password(new_password)
    db.commit()
    # A password reset is a strong signal of intent to invalidate any other
    # session that might be compromised.
    revoke_all_sessions(db, user)


def request_email_verification(db: Session, user: User) -> None:
    if user.email_verified:
        return
    raw_token = _issue_token(db, user, PURPOSE_EMAIL_VERIFY, EMAIL_VERIFY_TOKEN_TTL)
    link = f"{FRONTEND_URL}/verify-email?token={raw_token}"
    send_email(
        user.email,
        "Verify your email address",
        f"Use this link to verify your email (expires in 24 hours):\n{link}",
    )


def verify_email(db: Session, raw_token: str) -> User:
    token = _consume_token(db, raw_token, PURPOSE_EMAIL_VERIFY)
    user = db.get(User, token.user_id)
    if user is None:
        raise InvalidOrExpiredTokenError("This link is invalid or has expired. Please request a new one.")
    user.email_verified = True
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, *, current_password: str, new_password: str, keep_session_id: str | None) -> None:
    if not verify_password(current_password, user.password_hash):
        raise InvalidCredentialsError("Current password is incorrect.")
    user.password_hash = hash_password(new_password)
    db.commit()
    sessions = db.scalars(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    ).all()
    for session in sessions:
        if session.id != keep_session_id:
            session.revoked_at = _utcnow()
    db.commit()


def request_email_change(db: Session, user: User, *, new_email: str, current_password: str) -> None:
    new_email = _normalize_email(new_email)
    if not verify_password(current_password, user.password_hash):
        raise InvalidCredentialsError("Current password is incorrect.")
    if get_user_by_email(db, new_email) is not None:
        raise EmailAlreadyRegisteredError("An account with this email already exists.")
    raw_token = _issue_token(db, user, PURPOSE_EMAIL_CHANGE, EMAIL_CHANGE_TOKEN_TTL, new_email=new_email)
    link = f"{FRONTEND_URL}/settings/account?email_change_token={raw_token}"
    send_email(
        new_email,
        "Confirm your new email address",
        f"Use this link to confirm this address for your account (expires in 1 hour):\n{link}",
    )


def confirm_email_change(db: Session, raw_token: str) -> User:
    token = _consume_token(db, raw_token, PURPOSE_EMAIL_CHANGE)
    user = db.get(User, token.user_id)
    if user is None or not token.new_email:
        raise InvalidOrExpiredTokenError("This link is invalid or has expired. Please request a new one.")
    if get_user_by_email(db, token.new_email) is not None:
        raise EmailAlreadyRegisteredError("An account with this email already exists.")
    user.email = token.new_email
    user.email_verified = True  # the confirmation link itself was delivered to (and clicked from) the new address
    db.commit()
    db.refresh(user)
    return user


def delete_account(db: Session, user: User) -> None:
    """Hard-deletes the user row. ON DELETE CASCADE (see app.models_db)
    removes every private owned record: preferences, sessions, tokens,
    notifications, watchlists, paper portfolios, and experiments. Past
    support requests are retained with the account link nulled (ON DELETE
    SET NULL) for operational continuity - see docs/AUTHENTICATION.md."""
    db.delete(user)
    db.commit()
