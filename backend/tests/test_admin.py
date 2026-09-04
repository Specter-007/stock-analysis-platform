"""Minimal admin foundation: backend-enforced (never exposed to normal
users), scoped to basic user/account status and support-ticket triage only.
"""
from app.db.base import get_db
from app.main import app
from tests.conftest import register_and_login


def _csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def _promote_to_admin(email: str) -> None:
    from app.auth import service as auth_service
    from app.models_db.user import ROLE_ADMIN

    db = next(app.dependency_overrides[get_db]())
    user = auth_service.get_user_by_email(db, email)
    user.role = ROLE_ADMIN
    db.commit()
    db.close()


def test_normal_user_cannot_list_users(api_client):
    register_and_login(api_client, "normal-user@example.com")
    resp = api_client.get("/api/admin/users")
    assert resp.status_code == 401


def test_admin_can_list_users(api_client):
    register_and_login(api_client, "admin-user@example.com")
    _promote_to_admin("admin-user@example.com")
    resp = api_client.get("/api/admin/users")
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()["users"]]
    assert "admin-user@example.com" in emails


def test_admin_can_deactivate_a_user(api_client):
    register_and_login(api_client, "admin-user2@example.com")
    _promote_to_admin("admin-user2@example.com")

    from app.auth import service as auth_service

    db = next(app.dependency_overrides[get_db]())
    other = auth_service.register(db, email="target@example.com", password="abc12345", display_name="Target")
    db.close()

    resp = api_client.post(
        f"/api/admin/users/{other.id}/active", json={"is_active": False}, headers=_csrf_headers(api_client)
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # A deactivated account can no longer log in (generic invalid-credentials error).
    login_resp = api_client.post("/api/auth/login", json={"email": "target@example.com", "password": "abc12345"})
    assert login_resp.status_code == 401


def test_admin_can_list_and_update_support_requests(api_client):
    register_and_login(api_client, "admin-user3@example.com")
    _promote_to_admin("admin-user3@example.com")

    from app.rate_limit import limiter

    limiter.reset()
    create_resp = api_client.post(
        "/api/support",
        json={"contact_email": "x@example.com", "category": "BUG_REPORT", "subject": "s", "message": "m"},
    )
    ticket_id = create_resp.json()["id"]

    list_resp = api_client.get("/api/admin/support-requests")
    assert list_resp.status_code == 200
    assert any(r["id"] == ticket_id for r in list_resp.json()["requests"])

    update_resp = api_client.patch(
        f"/api/admin/support-requests/{ticket_id}", json={"status": "CLOSED"}, headers=_csrf_headers(api_client)
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "CLOSED"


def test_admin_endpoints_require_csrf(api_client):
    register_and_login(api_client, "admin-user4@example.com")
    _promote_to_admin("admin-user4@example.com")
    resp = api_client.post("/api/admin/users/does-not-matter/active", json={"is_active": False})
    assert resp.status_code == 403
