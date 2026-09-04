"""FastAPI dependencies for authentication, authorization, and CSRF -
imported by every router that needs to know "who is asking" or enforce
"is this actually theirs."

Ownership enforcement pattern used throughout the app: a resource lookup
function takes (db, user, resource_id) and raises ResourceNotFoundError
for BOTH "no such resource" and "belongs to someone else" - see
app.auth.exceptions.ResourceNotFoundError. Never trust a client-supplied
user_id; always derive the acting user from the session cookie via
`get_current_user`.
"""
from __future__ import annotations

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.orm import Session

from app.auth import service as auth_service
from app.auth.exceptions import AuthError, NotAuthenticatedError
from app.auth.security import verify_csrf_token
from app.db.base import get_db
from app.models_db.session import UserSession
from app.models_db.user import ROLE_ADMIN, User
from app.settings import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CsrfError(AuthError):
    pass


def get_current_session(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> tuple[User, UserSession]:
    if not session_token:
        raise NotAuthenticatedError("Not signed in.")
    result = auth_service.get_user_by_session_token(db, session_token)
    if result is None:
        raise NotAuthenticatedError("Your session has expired. Please sign in again.")
    user, session = result
    auth_service.touch_session(db, session)
    return user, session


def get_current_user(auth: tuple[User, UserSession] = Depends(get_current_session)) -> User:
    return auth[0]


def get_optional_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User | None:
    if not session_token:
        return None
    result = auth_service.get_user_by_session_token(db, session_token)
    if result is None:
        return None
    user, session = result
    auth_service.touch_session(db, session)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != ROLE_ADMIN:
        # Deliberately the same "not authenticated"-style shape rather than
        # confirming that an admin-only route exists to a normal user.
        raise NotAuthenticatedError("Not authorized.")
    return user


def require_csrf(
    request: Request,
    auth: tuple[User, UserSession] = Depends(get_current_session),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    csrf_header: str | None = Header(default=None, alias=CSRF_HEADER_NAME),
) -> User:
    """Double-submit-cookie CSRF check for state-changing authenticated
    requests: the signed CSRF cookie value must be echoed back verbatim in
    the X-CSRF-Token header (unreadable cross-origin without the cookie's
    JS-visible value) AND must verify as signed for this exact session."""
    user, session = auth
    if request.method not in _SAFE_METHODS:
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            raise CsrfError("Missing or invalid CSRF token.")
        if not verify_csrf_token(csrf_header, session.id):
            raise CsrfError("Missing or invalid CSRF token.")
    return user
