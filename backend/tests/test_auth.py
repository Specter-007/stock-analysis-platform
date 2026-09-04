"""SaaS foundation: authentication, session, and account-lifecycle tests -
exercised through the real HTTP layer (see the `api_client` fixture in
conftest.py) so cookie handling, CSRF enforcement, and rate limiting are
covered exactly as a real browser would hit them.
"""
from sqlalchemy import select

from app.models_db.tokens import AuthToken
from tests.conftest import register_and_login


def _csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


# --- Registration ---

def test_register_creates_account_and_session_cookies(api_client):
    resp = api_client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "abc12345", "display_name": "Alice"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["email_verified"] is False
    assert "session_token" in api_client.cookies
    assert "csrf_token" in api_client.cookies


def test_register_duplicate_email_returns_409(api_client):
    register_and_login(api_client, "dup@example.com")
    resp = api_client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "abc12345", "display_name": "Someone Else"},
    )
    assert resp.status_code == 409
    assert resp.json()["error_type"] == "EMAIL_ALREADY_REGISTERED"


def test_register_rejects_weak_password(api_client):
    resp = api_client.post(
        "/api/auth/register",
        json={"email": "weak@example.com", "password": "short", "display_name": "Weak"},
    )
    assert resp.status_code == 422


def test_register_rejects_invalid_email(api_client):
    resp = api_client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "abc12345", "display_name": "X"},
    )
    assert resp.status_code == 422


# --- Login / logout ---

def test_login_succeeds_with_correct_credentials(api_client):
    register_and_login(api_client, "bob@example.com", password="correcthorse1")
    api_client.post("/api/auth/logout")
    resp = api_client.post("/api/auth/login", json={"email": "bob@example.com", "password": "correcthorse1"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "bob@example.com"


def test_login_wrong_password_and_unknown_email_return_identical_generic_error(api_client):
    register_and_login(api_client, "carol@example.com", password="correcthorse1")
    api_client.post("/api/auth/logout")

    wrong_pw = api_client.post("/api/auth/login", json={"email": "carol@example.com", "password": "wrongpassword"})
    unknown_email = api_client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrongpassword"})

    assert wrong_pw.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_pw.json() == unknown_email.json()


def test_me_requires_authentication(api_client):
    resp = api_client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "NOT_AUTHENTICATED"


def test_logout_clears_session_so_me_becomes_unauthenticated(api_client):
    register_and_login(api_client, "dave@example.com")
    assert api_client.get("/api/auth/me").status_code == 200
    api_client.post("/api/auth/logout")
    assert api_client.get("/api/auth/me").status_code == 401


# --- CSRF ---

def test_state_changing_request_without_csrf_header_is_rejected(api_client):
    register_and_login(api_client, "eve@example.com", password="abc12345")
    resp = api_client.post(
        "/api/auth/change-password", json={"current_password": "abc12345", "new_password": "newpass123"}
    )
    assert resp.status_code == 403
    assert resp.json()["error_type"] == "CSRF_ERROR"


def test_state_changing_request_with_wrong_csrf_header_is_rejected(api_client):
    register_and_login(api_client, "frank@example.com", password="abc12345")
    resp = api_client.post(
        "/api/auth/change-password",
        json={"current_password": "abc12345", "new_password": "newpass123"},
        headers={"X-CSRF-Token": "not-the-real-token"},
    )
    assert resp.status_code == 403


def test_state_changing_request_with_correct_csrf_header_succeeds(api_client):
    register_and_login(api_client, "grace@example.com", password="abc12345")
    resp = api_client.post(
        "/api/auth/change-password",
        json={"current_password": "abc12345", "new_password": "newpass123"},
        headers=_csrf_headers(api_client),
    )
    assert resp.status_code == 200


# --- Password reset ---

def test_password_reset_request_response_identical_for_existing_and_unknown_email(api_client, db_session):
    register_and_login(api_client, "henry@example.com")
    known = api_client.post("/api/auth/password-reset/request", json={"email": "henry@example.com"})
    unknown = api_client.post("/api/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()


def test_password_reset_request_actually_issues_a_token_row(api_client, db_session):
    """HTTP-level check that a real AuthToken row is created (the raw token
    itself is only ever observable via the emailed link - by design it can't
    be recovered from the DB - so the full reset flow is verified at the
    service layer in test_password_reset_service_layer_full_flow_and_invalidates_sessions)."""
    register_and_login(api_client, "iris@example.com", password="oldpassword1")
    api_client.post("/api/auth/password-reset/request", json={"email": "iris@example.com"})

    from app.db.base import get_db
    from app.main import app

    override = app.dependency_overrides[get_db]
    db = next(override())
    token_row = db.scalar(select(AuthToken).where(AuthToken.purpose == "PASSWORD_RESET"))
    assert token_row is not None
    assert token_row.used_at is None
    db.close()


def test_password_reset_confirm_rejects_invalid_token(api_client):
    resp = api_client.post(
        "/api/auth/password-reset/confirm", json={"token": "not-a-real-token", "new_password": "newpass123"}
    )
    assert resp.status_code == 400
    assert resp.json()["error_type"] == "INVALID_OR_EXPIRED_TOKEN"


def test_password_reset_service_layer_full_flow_and_invalidates_sessions(db_session):
    from app.auth import service as auth_service

    user = auth_service.register(db_session, email="joan@example.com", password="oldpassword1", display_name="Joan")
    session, _raw = auth_service.create_session(db_session, user, user_agent=None, ip_address=None)
    assert auth_service.get_user_by_session_token(db_session, _raw) is not None

    raw_reset_token = auth_service._issue_token(
        db_session, user, "PASSWORD_RESET", auth_service.PASSWORD_RESET_TOKEN_TTL
    )
    auth_service.reset_password(db_session, raw_reset_token, "newpassword2")

    # Old password no longer works.
    import pytest

    from app.auth.exceptions import InvalidCredentialsError

    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate(db_session, email="joan@example.com", password="oldpassword1")

    # New password works.
    auth_service.authenticate(db_session, email="joan@example.com", password="newpassword2")

    # The pre-reset session was revoked as a side effect.
    assert auth_service.get_user_by_session_token(db_session, _raw) is None


def test_password_reset_token_is_single_use(db_session):
    import pytest

    from app.auth import service as auth_service
    from app.auth.exceptions import InvalidOrExpiredTokenError

    user = auth_service.register(db_session, email="kim@example.com", password="oldpassword1", display_name="Kim")
    raw_token = auth_service._issue_token(db_session, user, "PASSWORD_RESET", auth_service.PASSWORD_RESET_TOKEN_TTL)
    auth_service.reset_password(db_session, raw_token, "newpassword2")

    with pytest.raises(InvalidOrExpiredTokenError):
        auth_service.reset_password(db_session, raw_token, "yetanotherpassword3")


def test_password_reset_token_expires(db_session):
    import pytest
    from datetime import timedelta

    from app.auth import service as auth_service
    from app.auth.exceptions import InvalidOrExpiredTokenError
    from app.db.timeutil import utcnow_naive

    user = auth_service.register(db_session, email="liam@example.com", password="oldpassword1", display_name="Liam")
    raw_token = auth_service._issue_token(db_session, user, "PASSWORD_RESET", timedelta(hours=1))
    token_row = db_session.scalar(select(AuthToken).where(AuthToken.user_id == user.id))
    token_row.expires_at = utcnow_naive() - timedelta(minutes=1)
    db_session.commit()

    with pytest.raises(InvalidOrExpiredTokenError):
        auth_service.reset_password(db_session, raw_token, "newpassword2")


# --- Email verification ---

def test_email_verification_full_flow(db_session):
    from app.auth import service as auth_service

    user = auth_service.register(db_session, email="mia@example.com", password="abc12345", display_name="Mia")
    assert user.email_verified is False
    raw_token = auth_service._issue_token(db_session, user, "EMAIL_VERIFY", auth_service.EMAIL_VERIFY_TOKEN_TTL)
    verified_user = auth_service.verify_email(db_session, raw_token)
    assert verified_user.email_verified is True


def test_email_verification_confirm_rejects_invalid_token(api_client):
    resp = api_client.post("/api/auth/email-verification/confirm", json={"token": "bogus"})
    assert resp.status_code == 400


# --- Change password / change email ---

def test_change_password_rejects_wrong_current_password(api_client):
    register_and_login(api_client, "noah@example.com", password="abc12345")
    resp = api_client.post(
        "/api/auth/change-password",
        json={"current_password": "totallywrong", "new_password": "newpass123"},
        headers=_csrf_headers(api_client),
    )
    assert resp.status_code == 401


def test_change_email_requires_correct_password_and_rejects_duplicate(api_client):
    register_and_login(api_client, "olivia@example.com", password="abc12345")
    register_and_login(api_client, "taken@example.com", password="abc12345")
    api_client.post("/api/auth/logout")
    login_resp = api_client.post("/api/auth/login", json={"email": "olivia@example.com", "password": "abc12345"})
    assert login_resp.status_code == 200

    wrong_pw = api_client.post(
        "/api/auth/change-email/request",
        json={"new_email": "olivia2@example.com", "current_password": "wrongpassword"},
        headers=_csrf_headers(api_client),
    )
    assert wrong_pw.status_code == 401

    dup = api_client.post(
        "/api/auth/change-email/request",
        json={"new_email": "taken@example.com", "current_password": "abc12345"},
        headers=_csrf_headers(api_client),
    )
    assert dup.status_code == 409


# --- Sessions ---

def test_sessions_lists_current_session(api_client):
    register_and_login(api_client, "peter@example.com")
    resp = api_client.get("/api/auth/sessions")
    assert resp.status_code == 200
    sessions = resp.json()["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["is_current"] is True


def test_revoke_specific_session_then_it_cannot_be_used(db_session):
    from app.auth import service as auth_service

    user = auth_service.register(db_session, email="quinn@example.com", password="abc12345", display_name="Quinn")
    session, raw_token = auth_service.create_session(db_session, user, user_agent=None, ip_address=None)
    assert auth_service.get_user_by_session_token(db_session, raw_token) is not None

    assert auth_service.revoke_session(db_session, user, session.id) is True
    assert auth_service.get_user_by_session_token(db_session, raw_token) is None


def test_revoke_session_belonging_to_another_user_fails(db_session):
    from app.auth import service as auth_service

    user_a = auth_service.register(db_session, email="a@example.com", password="abc12345", display_name="A")
    user_b = auth_service.register(db_session, email="b@example.com", password="abc12345", display_name="B")
    session_b, raw_token_b = auth_service.create_session(db_session, user_b, user_agent=None, ip_address=None)

    assert auth_service.revoke_session(db_session, user_a, session_b.id) is False
    # Session B is untouched by user A's attempt.
    assert auth_service.get_user_by_session_token(db_session, raw_token_b) is not None


def test_revoke_others_keeps_current_session_alive(api_client):
    register_and_login(api_client, "river@example.com")
    resp = api_client.post("/api/auth/sessions/revoke-others", headers=_csrf_headers(api_client))
    assert resp.status_code == 200
    assert api_client.get("/api/auth/me").status_code == 200


# --- Account deletion ---

def test_delete_account_removes_owned_data(db_session):
    from app.auth import service as auth_service
    from app.models_db.watchlist import WatchlistDB

    user = auth_service.register(db_session, email="sam@example.com", password="abc12345", display_name="Sam")
    db_session.add(WatchlistDB(user_id=user.id, slug="default", tickers=["AAPL"]))
    db_session.commit()

    auth_service.delete_account(db_session, user)

    assert auth_service.get_user_by_id(db_session, user.id) is None
    assert db_session.query(WatchlistDB).count() == 0


def test_delete_account_via_http_requires_csrf_and_clears_cookies(api_client):
    register_and_login(api_client, "tina@example.com", password="abc12345")

    no_csrf = api_client.request("DELETE", "/api/auth/account")
    assert no_csrf.status_code == 403

    resp = api_client.request("DELETE", "/api/auth/account", headers=_csrf_headers(api_client))
    assert resp.status_code == 200
    assert api_client.get("/api/auth/me").status_code == 401


# --- Rate limiting ---

def test_login_endpoint_is_rate_limited(api_client):
    from app.rate_limit import limiter

    limiter.reset()
    register_and_login(api_client, "ursula@example.com", password="abc12345")
    api_client.post("/api/auth/logout")

    statuses = []
    for _ in range(10):
        resp = api_client.post("/api/auth/login", json={"email": "ursula@example.com", "password": "wrongpassword"})
        statuses.append(resp.status_code)
    assert 429 in statuses, f"expected a 429 among {statuses} after exceeding the login rate limit"
