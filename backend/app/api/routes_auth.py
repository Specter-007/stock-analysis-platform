from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.auth import service as auth_service
from app.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.auth.dependencies import get_current_session, get_current_user, require_csrf
from app.auth.schemas import (
    ChangeEmailConfirmRequest,
    ChangeEmailRequest,
    ChangePasswordRequest,
    EmailVerificationConfirmRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequestRequest,
    RegisterRequest,
    SessionListResponse,
    SessionResponse,
    UserResponse,
)
from app.auth.security import sign_csrf_token
from app.db.base import get_db
from app.models_db.session import UserSession
from app.models_db.user import User
from app.rate_limit import limiter
from app.settings import RATE_LIMIT_AUTH, RATE_LIMIT_PASSWORD_RESET

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        email_verified=user.email_verified,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _issue_login_cookies(response: Response, db: Session, user: User, request: Request) -> None:
    session, raw_token = auth_service.create_session(
        db, user, user_agent=request.headers.get("user-agent"), ip_address=_client_ip(request)
    )
    csrf_token = sign_csrf_token(session.id)
    set_auth_cookies(response, session_token=raw_token, csrf_token=csrf_token)


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit(RATE_LIMIT_AUTH)
def register(request: Request, body: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.register(
        db, email=body.email, password=body.password, display_name=body.display_name,
        marketing_consent=body.marketing_consent,
    )
    auth_service.request_email_verification(db, user)
    _issue_login_cookies(response, db, user, request)
    return _user_response(user)


@router.post("/login", response_model=UserResponse)
@limiter.limit(RATE_LIMIT_AUTH)
def login(request: Request, body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, email=body.email, password=body.password)
    _issue_login_cookies(response, db, user, request)
    return _user_response(user)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response, auth: tuple[User, UserSession] = Depends(get_current_session), db: Session = Depends(get_db)):
    _, session = auth
    auth_service.revoke_session(db, auth[0], session.id)
    clear_auth_cookies(response)
    return MessageResponse(message="Signed out.")


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _user_response(user)


@router.post("/password-reset/request", response_model=MessageResponse)
@limiter.limit(RATE_LIMIT_PASSWORD_RESET)
def request_password_reset(request: Request, body: PasswordResetRequestRequest, db: Session = Depends(get_db)):
    auth_service.request_password_reset(db, body.email)
    # Deliberately identical response whether or not the email is registered.
    return MessageResponse(message="If an account with that email exists, a password reset link has been sent.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(body: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, body.token, body.new_password)
    return MessageResponse(message="Password has been reset. Please sign in again.")


@router.post("/email-verification/request", response_model=MessageResponse)
@limiter.limit(RATE_LIMIT_PASSWORD_RESET)
def request_email_verification(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service.request_email_verification(db, user)
    return MessageResponse(message="A verification link has been sent to your email address.")


@router.post("/email-verification/confirm", response_model=UserResponse)
def confirm_email_verification(body: EmailVerificationConfirmRequest, db: Session = Depends(get_db)):
    user = auth_service.verify_email(db, body.token)
    return _user_response(user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    body: ChangePasswordRequest,
    auth: tuple[User, UserSession] = Depends(get_current_session),
    _csrf: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    user, session = auth
    auth_service.change_password(
        db, user, current_password=body.current_password, new_password=body.new_password, keep_session_id=session.id
    )
    return MessageResponse(message="Password changed. You have been signed out of your other sessions.")


@router.post("/change-email/request", response_model=MessageResponse)
def request_email_change(
    body: ChangeEmailRequest, user: User = Depends(get_current_user), _csrf: User = Depends(require_csrf), db: Session = Depends(get_db)
):
    auth_service.request_email_change(db, user, new_email=body.new_email, current_password=body.current_password)
    return MessageResponse(message="A confirmation link has been sent to the new email address.")


@router.post("/change-email/confirm", response_model=UserResponse)
def confirm_email_change(body: ChangeEmailConfirmRequest, db: Session = Depends(get_db)):
    user = auth_service.confirm_email_change(db, body.token)
    return _user_response(user)


@router.delete("/account", response_model=MessageResponse)
def delete_account(
    response: Response, user: User = Depends(get_current_user), _csrf: User = Depends(require_csrf), db: Session = Depends(get_db)
):
    auth_service.delete_account(db, user)
    clear_auth_cookies(response)
    return MessageResponse(message="Your account and all associated data have been deleted.")


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(auth: tuple[User, UserSession] = Depends(get_current_session), db: Session = Depends(get_db)):
    user, current_session = auth
    sessions = auth_service.list_sessions(db, user)
    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                created_at=s.created_at,
                last_seen_at=s.last_seen_at,
                expires_at=s.expires_at,
                user_agent=s.user_agent,
                is_current=(s.id == current_session.id),
            )
            for s in sessions
        ]
    )


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def revoke_session(
    session_id: str,
    user: User = Depends(get_current_user),
    _csrf: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    from app.auth.exceptions import ResourceNotFoundError

    if not auth_service.revoke_session(db, user, session_id):
        raise ResourceNotFoundError("Session not found.")
    return MessageResponse(message="Session revoked.")


@router.post("/sessions/revoke-others", response_model=MessageResponse)
def revoke_other_sessions(
    auth: tuple[User, UserSession] = Depends(get_current_session),
    _csrf: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    user, session = auth
    count = auth_service.revoke_all_other_sessions(db, user, session.id)
    return MessageResponse(message=f"Signed out of {count} other session(s).")
