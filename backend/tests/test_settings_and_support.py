"""Settings/preferences (onboarding, timezone, benchmark, theme, consent)
and the contact/support endpoint - including its anonymous path and
rate limiting.
"""
from tests.conftest import register_and_login


def _csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


# ------------------------------------------------------------ Preferences

def test_new_account_has_default_preferences_and_recorded_consent(api_client):
    register_and_login(api_client, "prefs-a@example.com")
    resp = api_client.get("/api/settings/preferences")
    assert resp.status_code == 200
    body = resp.json()
    assert body["timezone"] == "UTC"
    assert body["default_benchmark"] == "SPY"
    assert body["onboarding_completed"] is False
    assert body["terms_accepted_at"] is not None
    assert body["marketing_consent"] is False  # default False, never implied by registering


def test_registering_with_marketing_consent_true_is_recorded(api_client):
    resp = api_client.post(
        "/api/auth/register",
        json={
            "email": "prefs-consent@example.com", "password": "abc12345", "display_name": "Consent",
            "accept_terms": True, "marketing_consent": True,
        },
    )
    assert resp.status_code == 201
    prefs = api_client.get("/api/settings/preferences").json()
    assert prefs["marketing_consent"] is True


def test_registering_without_accepting_terms_is_rejected(api_client):
    resp = api_client.post(
        "/api/auth/register",
        json={"email": "no-terms@example.com", "password": "abc12345", "display_name": "X", "accept_terms": False},
    )
    assert resp.status_code == 422


def test_update_preferences_requires_csrf(api_client):
    register_and_login(api_client, "prefs-b@example.com")
    no_csrf = api_client.patch("/api/settings/preferences", json={"theme": "light"})
    assert no_csrf.status_code == 403


def test_update_preferences_persists_changes(api_client):
    register_and_login(api_client, "prefs-c@example.com")
    resp = api_client.patch(
        "/api/settings/preferences",
        json={"timezone": "America/New_York", "default_benchmark": "qqq", "theme": "light"},
        headers=_csrf_headers(api_client),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["timezone"] == "America/New_York"
    assert body["default_benchmark"] == "QQQ"
    assert body["theme"] == "light"


def test_update_preferences_rejects_invalid_theme(api_client):
    register_and_login(api_client, "prefs-d@example.com")
    resp = api_client.patch("/api/settings/preferences", json={"theme": "neon"}, headers=_csrf_headers(api_client))
    assert resp.status_code == 422


def test_update_preferences_rejects_invalid_timezone(api_client):
    register_and_login(api_client, "prefs-e@example.com")
    resp = api_client.patch(
        "/api/settings/preferences", json={"timezone": "Not/AZone"}, headers=_csrf_headers(api_client)
    )
    assert resp.status_code == 422


def test_onboarding_completion(api_client):
    register_and_login(api_client, "prefs-f@example.com")
    assert api_client.get("/api/settings/preferences").json()["onboarding_completed"] is False
    resp = api_client.post("/api/settings/onboarding/complete", headers=_csrf_headers(api_client))
    assert resp.status_code == 200
    assert resp.json()["onboarding_completed"] is True
    assert resp.json()["onboarding_completed_at"] is not None


def test_preferences_require_authentication(api_client):
    from fastapi.testclient import TestClient
    from app.main import app

    anon = TestClient(app)
    assert anon.get("/api/settings/preferences").status_code == 401


# ----------------------------------------------------------------- Support

def test_anonymous_contact_request_succeeds(api_client):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.rate_limit import limiter

    limiter.reset()
    anon = TestClient(app)
    resp = anon.post(
        "/api/support",
        json={"contact_email": "visitor@example.com", "category": "BUG_REPORT", "subject": "Issue", "message": "Something broke."},
    )
    assert resp.status_code == 200
    assert "id" in resp.json()


def test_authenticated_contact_request_is_associated_with_account(api_client):
    from app.rate_limit import limiter

    limiter.reset()
    register_and_login(api_client, "support-user@example.com")
    resp = api_client.post(
        "/api/support",
        json={"contact_email": "support-user@example.com", "category": "ACCOUNT", "subject": "Question", "message": "How do I export data?"},
    )
    assert resp.status_code == 200

    from app.db.base import get_db
    from app.main import app

    db = next(app.dependency_overrides[get_db]())
    from app.auth import service as auth_service
    from app.support import service as support_service

    user = auth_service.get_user_by_email(db, "support-user@example.com")
    requests = support_service.list_my_support_requests(db, user.id)
    assert len(requests) == 1
    db.close()


def test_contact_rejects_invalid_category(api_client):
    from app.rate_limit import limiter

    limiter.reset()
    resp = api_client.post(
        "/api/support",
        json={"contact_email": "x@example.com", "category": "NOT_A_CATEGORY", "subject": "s", "message": "m"},
    )
    assert resp.status_code == 422


def test_contact_endpoint_is_rate_limited(api_client):
    from app.rate_limit import limiter

    limiter.reset()
    statuses = []
    for _ in range(10):
        resp = api_client.post(
            "/api/support",
            json={"contact_email": "spammer@example.com", "category": "OTHER", "subject": "s", "message": "m"},
        )
        statuses.append(resp.status_code)
    assert 429 in statuses
