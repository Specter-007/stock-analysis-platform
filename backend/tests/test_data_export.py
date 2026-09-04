"""GET /api/settings/export - full account data export. Verifies it
includes everything the user owns, excludes secrets, and never leaks
another user's data.
"""
from app.db.base import get_db
from app.main import app
from tests.conftest import register_and_login


def _csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def _db():
    return next(app.dependency_overrides[get_db]())


def test_export_requires_authentication(api_client):
    from fastapi.testclient import TestClient

    anon = TestClient(app)
    assert anon.get("/api/settings/export").status_code == 401


def test_export_includes_profile_and_preferences(api_client):
    register_and_login(api_client, "export-a@example.com")
    resp = api_client.get("/api/settings/export")
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"]["email"] == "export-a@example.com"
    assert body["preferences"]["default_benchmark"] == "SPY"
    assert body["preferences"]["terms_accepted_at"] is not None


def test_export_never_includes_password_hash_or_secrets(api_client):
    register_and_login(api_client, "export-b@example.com")
    resp = api_client.get("/api/settings/export")
    body = resp.json()
    dumped = str(body)
    assert "password_hash" not in dumped
    assert "token_hash" not in dumped
    assert "session_token" not in dumped


def test_export_includes_watchlist_paper_portfolio_and_experiment(api_client, ohlcv_long):
    register_and_login(api_client, "export-c@example.com")

    db = _db()
    from app.auth import service as auth_service
    from app.experiments import store as experiments_store
    from app.experiments.fingerprint import compute_fingerprint
    from app.experiments.models import Experiment, ExperimentConfig
    from app.paper_trading import store as paper_trading_store
    from app.watchlist import store as watchlist_store

    user = auth_service.get_user_by_email(db, "export-c@example.com")
    watchlist_store.save_tickers(db, user.id, "default", ["AAPL"])
    paper_trading_store.save_portfolio(db, user.id, "default", {"cash": 5000, "positions": {}, "trades": []})

    config = ExperimentConfig(
        model_version="1.1", tickers=["AAPL"], benchmark="SPY", start_date="2023-01-01",
        end_date="2024-01-01", initial_capital=10000.0, commission_bps=5.0, slippage_bps=5.0,
    )
    experiment = Experiment(
        id=experiments_store.new_experiment_id(), name="Export test", created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00", status="DRAFT", config=config, fingerprint=compute_fingerprint(config),
    )
    experiments_store.save_experiment(db, user.id, experiment)
    db.close()

    resp = api_client.get("/api/settings/export")
    body = resp.json()
    assert body["watchlists"][0]["tickers"] == ["AAPL"]
    assert body["paper_portfolios"][0]["state"]["cash"] == 5000
    assert body["experiments"][0]["name"] == "Export test"


def test_export_never_includes_another_users_data(api_client):
    from fastapi.testclient import TestClient

    client_a = api_client
    client_b = TestClient(app)
    register_and_login(client_a, "export-user-a@example.com")
    register_and_login(client_b, "export-user-b@example.com")

    db = _db()
    from app.auth import service as auth_service
    from app.watchlist import store as watchlist_store

    user_a = auth_service.get_user_by_email(db, "export-user-a@example.com")
    watchlist_store.save_tickers(db, user_a.id, "default", ["SECRET_TICKER"])
    db.close()

    b_export = client_b.get("/api/settings/export").json()
    assert b_export["watchlists"] == []
    assert "SECRET_TICKER" not in str(b_export)


def test_export_is_a_downloadable_attachment(api_client):
    register_and_login(api_client, "export-d@example.com")
    resp = api_client.get("/api/settings/export")
    assert "attachment" in resp.headers.get("content-disposition", "")
