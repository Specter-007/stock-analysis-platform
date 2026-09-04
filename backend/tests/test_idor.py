"""SaaS foundation: IDOR (Insecure Direct Object Reference) prevention -
critical security tests confirming User A can never GET/PATCH/POST/DELETE
User B's watchlists, paper portfolios, or experiments over the real HTTP
API. Two independent TestClient instances (separate cookie jars) share the
same isolated in-memory database via `api_client`'s dependency override, so
both users genuinely exist in one database - exactly the scenario a real
attacker would be in.
"""
from fastapi.testclient import TestClient

from app.main import app


def _second_client() -> TestClient:
    """A second, independently-cookied client against the SAME overridden
    database as `api_client` (the override lives on the shared `app`
    object, not on any one TestClient instance)."""
    return TestClient(app)


def _csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def _register(client, email, password="abc12345", display_name="Test"):
    resp = client.post("/api/auth/register", json={"email": email, "password": password, "display_name": display_name})
    assert resp.status_code == 201, resp.text
    return resp.json()


# --------------------------------------------------------------- Watchlist

def test_user_b_cannot_see_user_a_watchlist_tickers(api_client):
    client_a = api_client
    client_b = _second_client()
    _register(client_a, "wl-a@example.com")
    _register(client_b, "wl-b@example.com")

    add = client_a.post("/api/watchlist", json={"watchlist_id": "default", "ticker": "AAPL"}, headers=_csrf_headers(client_a))
    assert add.status_code == 200

    b_view = client_b.get("/api/watchlist", params={"watchlist_id": "default"})
    assert b_view.status_code == 200
    assert b_view.json()["tickers"] == []


def test_user_b_delete_does_not_affect_user_a_watchlist(api_client):
    client_a = api_client
    client_b = _second_client()
    _register(client_a, "wl-a2@example.com")
    _register(client_b, "wl-b2@example.com")

    client_a.post("/api/watchlist", json={"watchlist_id": "default", "ticker": "AAPL"}, headers=_csrf_headers(client_a))
    # User B attempts to remove a ticker from "their own" default watchlist -
    # this can only ever touch B's own (empty) watchlist, never A's.
    client_b.delete("/api/watchlist/AAPL", params={"watchlist_id": "default"}, headers=_csrf_headers(client_b))

    a_view = client_a.get("/api/watchlist", params={"watchlist_id": "default"})
    assert a_view.json()["tickers"] == ["AAPL"]


# ----------------------------------------------------------- Paper trading

def test_user_b_cannot_see_user_a_paper_portfolio(api_client):
    client_a = api_client
    client_b = _second_client()
    _register(client_a, "pt-a@example.com")
    _register(client_b, "pt-b@example.com")

    reset = client_a.post(
        "/api/paper-portfolio/reset",
        params={"portfolio_id": "default", "starting_capital": 25_000},
        headers=_csrf_headers(client_a),
    )
    assert reset.status_code == 200
    assert reset.json()["starting_capital"] == 25_000

    b_view = client_b.get("/api/paper-portfolio", params={"portfolio_id": "default"})
    assert b_view.status_code == 200
    assert b_view.json()["starting_capital"] == 10_000.0  # B's own default, untouched by A


def test_user_b_paper_portfolios_listing_never_includes_user_a(api_client):
    client_a = api_client
    client_b = _second_client()
    _register(client_a, "pt-list-a@example.com")
    _register(client_b, "pt-list-b@example.com")

    client_a.post("/api/paper-portfolio/reset", params={"portfolio_id": "alpha"}, headers=_csrf_headers(client_a))
    client_b.post("/api/paper-portfolio/reset", params={"portfolio_id": "beta"}, headers=_csrf_headers(client_b))

    b_list = client_b.get("/api/paper-portfolios")
    ids = [p["portfolio_id"] for p in b_list.json()["portfolios"]]
    assert "alpha" not in ids
    assert "beta" in ids


# ------------------------------------------------------------- Experiments

def _minimal_experiment_payload():
    return {
        "name": "IDOR test experiment",
        "config": {
            "model_version": "1.1",
            "tickers": ["AAPL"],
            "benchmark": "SPY",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "initial_capital": 10000.0,
            "commission_bps": 5.0,
            "slippage_bps": 5.0,
        },
    }


def test_user_b_cannot_get_user_a_experiment(api_client):
    client_a = api_client
    client_b = _second_client()
    _register(client_a, "exp-a@example.com")
    _register(client_b, "exp-b@example.com")

    created = client_a.post("/api/experiments", json=_minimal_experiment_payload(), headers=_csrf_headers(client_a))
    assert created.status_code == 200
    experiment_id = created.json()["id"]

    resp = client_b.get(f"/api/experiments/{experiment_id}")
    assert resp.status_code == 404


def test_user_b_cannot_delete_user_a_experiment(api_client):
    client_a = api_client
    client_b = _second_client()
    _register(client_a, "exp-a2@example.com")
    _register(client_b, "exp-b2@example.com")

    created = client_a.post("/api/experiments", json=_minimal_experiment_payload(), headers=_csrf_headers(client_a))
    experiment_id = created.json()["id"]

    delete_resp = client_b.delete(f"/api/experiments/{experiment_id}", headers=_csrf_headers(client_b))
    assert delete_resp.status_code == 404

    still_there = client_a.get(f"/api/experiments/{experiment_id}")
    assert still_there.status_code == 200


def test_user_b_cannot_patch_user_a_experiment_notes(api_client):
    client_a = api_client
    client_b = _second_client()
    _register(client_a, "exp-a3@example.com")
    _register(client_b, "exp-b3@example.com")

    created = client_a.post("/api/experiments", json=_minimal_experiment_payload(), headers=_csrf_headers(client_a))
    experiment_id = created.json()["id"]

    patch_resp = client_b.patch(
        f"/api/experiments/{experiment_id}/notes",
        json={"notes": "hijacked"},
        headers=_csrf_headers(client_b),
    )
    assert patch_resp.status_code == 404

    original = client_a.get(f"/api/experiments/{experiment_id}")
    assert original.json()["notes"] != "hijacked"


def test_user_b_experiment_list_never_includes_user_a_experiments(api_client):
    client_a = api_client
    client_b = _second_client()
    _register(client_a, "exp-list-a@example.com")
    _register(client_b, "exp-list-b@example.com")

    created = client_a.post("/api/experiments", json=_minimal_experiment_payload(), headers=_csrf_headers(client_a))
    experiment_id = created.json()["id"]

    b_list = client_b.get("/api/experiments")
    ids = [row["experiment"]["id"] for row in b_list.json()["experiments"]]
    assert experiment_id not in ids


def test_user_b_cannot_run_user_a_experiment(api_client):
    client_a = api_client
    client_b = _second_client()
    _register(client_a, "exp-run-a@example.com")
    _register(client_b, "exp-run-b@example.com")

    created = client_a.post("/api/experiments", json=_minimal_experiment_payload(), headers=_csrf_headers(client_a))
    experiment_id = created.json()["id"]

    run_resp = client_b.post(f"/api/experiments/{experiment_id}/run", headers=_csrf_headers(client_b))
    assert run_resp.status_code == 404


# --------------------------------------------------------------- Unauthenticated

def test_all_three_subsystems_require_authentication(api_client):
    anon = _second_client()
    assert anon.get("/api/watchlist").status_code == 401
    assert anon.get("/api/paper-portfolio").status_code == 401
    assert anon.get("/api/experiments").status_code == 401
