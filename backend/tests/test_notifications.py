"""Notifications: created only from real events (never fabricated - see
app.notifications.service docstring), unread/read state, and IDOR
protection (User A can never read or mark-read User B's notifications).
"""
import pytest

from app.models_db.notification import TYPE_SYSTEM
from app.notifications import service as notifications_service
from tests.conftest import register_and_login


@pytest.fixture
def user_id(db_session):
    from app.models_db.user import User

    user = User(email="notif-test@example.com", password_hash="x", display_name="Test")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user.id


def _csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


# --------------------------------------------------------------- Service

def test_create_and_list_notification(db_session, user_id):
    notifications_service.create_notification(db_session, user_id, TYPE_SYSTEM, "Title", "Message body")
    rows = notifications_service.list_notifications(db_session, user_id)
    assert len(rows) == 1
    assert rows[0].title == "Title"
    assert rows[0].read_at is None


def test_unread_count_reflects_only_unread(db_session, user_id):
    a = notifications_service.create_notification(db_session, user_id, TYPE_SYSTEM, "A", "m")
    notifications_service.create_notification(db_session, user_id, TYPE_SYSTEM, "B", "m")
    assert notifications_service.unread_count(db_session, user_id) == 2

    notifications_service.mark_read(db_session, user_id, a.id)
    assert notifications_service.unread_count(db_session, user_id) == 1


def test_mark_all_read(db_session, user_id):
    for i in range(3):
        notifications_service.create_notification(db_session, user_id, TYPE_SYSTEM, f"N{i}", "m")
    marked = notifications_service.mark_all_read(db_session, user_id)
    assert marked == 3
    assert notifications_service.unread_count(db_session, user_id) == 0


def test_mark_read_for_another_users_notification_fails(db_session, user_id):
    from app.models_db.user import User

    other = User(email="notif-other@example.com", password_hash="x", display_name="Other")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    n = notifications_service.create_notification(db_session, other.id, TYPE_SYSTEM, "Theirs", "m")
    assert notifications_service.mark_read(db_session, user_id, n.id) is False
    assert notifications_service.unread_count(db_session, other.id) == 1


def test_unread_only_filter(db_session, user_id):
    a = notifications_service.create_notification(db_session, user_id, TYPE_SYSTEM, "A", "m")
    notifications_service.create_notification(db_session, user_id, TYPE_SYSTEM, "B", "m")
    notifications_service.mark_read(db_session, user_id, a.id)

    unread = notifications_service.list_notifications(db_session, user_id, unread_only=True)
    assert len(unread) == 1
    assert unread[0].title == "B"


# ------------------------------------------------------------------ HTTP

def test_notifications_require_authentication(api_client):
    assert api_client.get("/api/notifications").status_code == 401


def test_list_and_mark_read_over_http(api_client):
    from app.auth import service as auth_service
    from app.db.base import get_db
    from app.main import app

    register_and_login(api_client, "notif-http@example.com")

    db = next(app.dependency_overrides[get_db]())
    user = auth_service.get_user_by_email(db, "notif-http@example.com")
    notifications_service.create_notification(db, user.id, TYPE_SYSTEM, "Hello", "World")
    db.close()

    resp = api_client.get("/api/notifications")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["notifications"]) == 1
    assert body["unread_count"] == 1

    notif_id = body["notifications"][0]["id"]
    mark_resp = api_client.post(f"/api/notifications/{notif_id}/read", headers=_csrf_headers(api_client))
    assert mark_resp.status_code == 200

    resp2 = api_client.get("/api/notifications/unread-count")
    assert resp2.json()["unread_count"] == 0


def test_user_b_cannot_mark_user_a_notification_read(api_client):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.base import get_db

    client_a = api_client
    client_b = TestClient(app)
    register_and_login(client_a, "notif-a@example.com")
    register_and_login(client_b, "notif-b@example.com")

    override = app.dependency_overrides[get_db]
    db = next(override())
    from app.auth import service as auth_service

    user_a = auth_service.get_user_by_email(db, "notif-a@example.com")
    notif = notifications_service.create_notification(db, user_a.id, TYPE_SYSTEM, "A's notification", "m")
    db.close()

    resp = client_b.post(f"/api/notifications/{notif.id}/read", headers=_csrf_headers(client_b))
    assert resp.status_code == 404

    a_list = client_a.get("/api/notifications").json()
    assert a_list["notifications"][0]["read_at"] is None


# --------------------------------------------------------- Real-event triggers

def test_experiment_failure_creates_a_notification(db_session, user_id, ohlcv_long):
    from app.experiments import service as experiments_service
    from app.experiments.models import ExperimentConfig

    config = ExperimentConfig(
        model_version="1.1", tickers=["AAA"], benchmark="SPY",
        start_date=str(ohlcv_long.index[-5].date()), end_date=str(ohlcv_long.index[-1].date()),
        initial_capital=10_000.0, commission_bps=5.0, slippage_bps=5.0,
    )
    exp = experiments_service.create_experiment(db_session, user_id, config, name="Too short")
    ran = experiments_service.run_experiment(
        db_session, user_id, exp.id, price_data={"AAA": ohlcv_long}, benchmark_df=ohlcv_long, tickers_unavailable={}
    )
    assert ran.status == "FAILED"

    notifications = notifications_service.list_notifications(db_session, user_id)
    assert any(n.type == "EXPERIMENT_FAILED" for n in notifications)


def test_stop_loss_trigger_creates_a_paper_portfolio_notification(db_session, user_id, monkeypatch):
    from app.paper_trading import service as paper_trading_service

    prices = {"AAPL": 100.0}
    monkeypatch.setattr(paper_trading_service, "_current_price", lambda t: prices.get(t))
    monkeypatch.setattr(paper_trading_service, "_current_signal_snapshot", lambda t: (None, None))
    monkeypatch.setattr(paper_trading_service, "_current_market_regime", lambda: None)

    paper_trading_service.execute_trade(db_session, user_id, "sl_notif", "AAPL", "BUY", 10, stop_loss_percent=5.0)
    prices["AAPL"] = 90.0
    paper_trading_service.get_portfolio(db_session, user_id, "sl_notif")

    notifications = notifications_service.list_notifications(db_session, user_id)
    assert any(n.type == "PAPER_PORTFOLIO_EVENT" and "STOP_LOSS" in n.message for n in notifications)
