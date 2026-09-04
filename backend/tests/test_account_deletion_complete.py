"""Complete account-deletion verification (final production-hardening
pass, section 6): a user with a watchlist, an experiment, a paper
portfolio with trades, a notification, preferences, and a support request
is deleted - verify every owned record is gone (or, for support requests,
intentionally anonymized), sessions and auth tokens are invalidated, the
account can no longer authenticate, and none of its former resource IDs
remain accessible.
"""
from app.db.base import get_db
from app.main import app
from tests.conftest import register_and_login


def _csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def _db():
    return next(app.dependency_overrides[get_db]())


def test_full_account_deletion_removes_everything_owned(api_client):
    register_and_login(api_client, "delete-full@example.com", password="abc12345")

    db = _db()
    from app.auth import service as auth_service
    from app.experiments import store as experiments_store
    from app.experiments.fingerprint import compute_fingerprint
    from app.experiments.models import Experiment, ExperimentConfig

    user = auth_service.get_user_by_email(db, "delete-full@example.com")
    user_id = user.id

    from app.watchlist import store as watchlist_store
    from app.paper_trading import store as paper_trading_store
    from app.notifications import service as notifications_service
    from app.models_db.notification import TYPE_SYSTEM
    from app.support import service as support_service

    watchlist_store.save_tickers(db, user_id, "default", ["AAPL"])
    paper_trading_store.save_portfolio(
        db, user_id, "default",
        {"cash": 8000, "positions": {}, "trades": [{"ticker": "AAPL", "action": "BUY", "shares": 1}], "equity_snapshots": [], "benchmark_basis": None},
    )
    config = ExperimentConfig(
        model_version="1.1", tickers=["AAPL"], benchmark="SPY", start_date="2023-01-01",
        end_date="2024-01-01", initial_capital=10000.0, commission_bps=5.0, slippage_bps=5.0,
    )
    experiment = Experiment(
        id=experiments_store.new_experiment_id(), name="Deletion test", created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00", status="DRAFT", config=config, fingerprint=compute_fingerprint(config),
    )
    experiment_id = experiment.id
    experiments_store.save_experiment(db, user_id, experiment)
    notifications_service.create_notification(db, user_id, TYPE_SYSTEM, "Test", "Body")
    support_request = support_service.create_support_request(
        db, user_id=user_id, contact_email=user.email, category="BUG_REPORT", subject="s", message="m"
    )
    support_request_id = support_request.id
    # Also request an auth token (password reset) so we can prove it's gone too.
    raw_reset_token = auth_service._issue_token(db, user, "PASSWORD_RESET", auth_service.PASSWORD_RESET_TOKEN_TTL)
    db.close()

    # Confirm everything actually exists before deletion.
    assert api_client.get("/api/watchlist").json()["tickers"] == ["AAPL"]
    assert api_client.get(f"/api/experiments/{experiment_id}").status_code == 200
    assert api_client.get("/api/notifications").json()["unread_count"] == 1

    # --- Delete the account ---
    delete_resp = api_client.request("DELETE", "/api/auth/account", headers=_csrf_headers(api_client))
    assert delete_resp.status_code == 200

    # 1. Session is invalidated - /me is now unauthenticated.
    assert api_client.get("/api/auth/me").status_code == 401

    # 2. The account can no longer authenticate at all.
    login_resp = api_client.post("/api/auth/login", json={"email": "delete-full@example.com", "password": "abc12345"})
    assert login_resp.status_code == 401

    # 3. Every owned record is actually gone at the database level.
    db = _db()
    from app.models_db.experiment import ExperimentDB
    from app.models_db.notification import Notification
    from app.models_db.paper_trading import PaperPortfolioDB
    from app.models_db.session import UserSession
    from app.models_db.support import SupportRequest
    from app.models_db.tokens import AuthToken
    from app.models_db.user import User, UserPreferences
    from app.models_db.watchlist import WatchlistDB

    assert db.get(User, user_id) is None
    assert db.query(UserPreferences).filter_by(user_id=user_id).count() == 0
    assert db.query(UserSession).filter_by(user_id=user_id).count() == 0
    assert db.query(AuthToken).filter_by(user_id=user_id).count() == 0  # the password-reset token row is gone too
    assert db.query(WatchlistDB).filter_by(user_id=user_id).count() == 0
    assert db.query(PaperPortfolioDB).filter_by(user_id=user_id).count() == 0
    assert db.query(ExperimentDB).filter_by(id=experiment_id).count() == 0
    assert db.query(Notification).filter_by(user_id=user_id).count() == 0

    # 4. Support request is retained (operational continuity) but anonymized -
    #    not an orphaned *private* record since it no longer references the account.
    remaining_ticket = db.get(SupportRequest, support_request_id)
    assert remaining_ticket is not None
    assert remaining_ticket.user_id is None
    db.close()

    # 5. The now-consumed password-reset token can't be replayed (it's gone entirely).
    confirm_resp = api_client.post(
        "/api/auth/password-reset/confirm", json={"token": raw_reset_token, "new_password": "irrelevant123"}
    )
    assert confirm_resp.status_code == 400

    # 6. The old experiment id is unreachable even by a brand-new, unrelated account
    #    (proves it's not just hidden from the old session - the row is truly gone).
    register_and_login(api_client, "delete-full-checker@example.com")
    assert api_client.get(f"/api/experiments/{experiment_id}").status_code == 404
