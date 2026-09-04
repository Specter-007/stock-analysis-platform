"""Resource/input abuse testing (final production-hardening pass, section
13): the server must respond with a clean validation/size/rate-limit
error for hostile input - never crash, never leak a traceback, never grow
memory unboundedly.
"""
import json

from app.body_size_limit import MAX_REQUEST_BODY_BYTES
from tests.conftest import register_and_login


def _csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def test_oversized_request_body_is_rejected(api_client):
    huge_message = "x" * (MAX_REQUEST_BODY_BYTES + 1000)
    resp = api_client.post(
        "/api/support",
        content=json.dumps({"contact_email": "a@example.com", "category": "OTHER", "subject": "s", "message": huge_message}),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413
    assert resp.json()["error_type"] == "PAYLOAD_TOO_LARGE"


def test_malformed_json_returns_clean_422_not_a_traceback(api_client):
    resp = api_client.post(
        "/api/auth/login", content="{not valid json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 422
    assert "Traceback" not in resp.text


def test_field_exceeding_max_length_is_rejected_not_silently_truncated(api_client):
    register_and_login(api_client, "abuse-a@example.com")
    resp = api_client.post(
        "/api/support",
        json={"contact_email": "a@example.com", "category": "OTHER", "subject": "s", "message": "x" * 6000},
    )
    assert resp.status_code == 422


def test_excessive_tickers_in_portfolio_backtest_rejected(api_client):
    resp = api_client.post(
        "/api/backtest/portfolio",
        json={"tickers": [f"T{i}" for i in range(25)], "start_date": "2023-01-01", "end_date": "2024-01-01"},
    )
    assert resp.status_code == 422


def test_excessive_monte_carlo_simulations_rejected(api_client):
    resp = api_client.post(
        "/api/backtest/monte-carlo",
        json={"ticker": "AAPL", "start_date": "2023-01-01", "end_date": "2024-01-01", "simulations": 10_000_000},
    )
    assert resp.status_code == 422


def test_negative_initial_capital_rejected(api_client):
    resp = api_client.post(
        "/api/backtest",
        json={"ticker": "AAPL", "start_date": "2023-01-01", "end_date": "2024-01-01", "initial_capital": -5000},
    )
    assert resp.status_code == 422


def test_nan_and_infinity_in_json_body_rejected(api_client):
    # Python's json module accepts NaN/Infinity by default (non-standard
    # JSON extension) - a client could send them as raw bytes even though
    # `requests`/httpx's own json= helper would not construct them normally.
    resp = api_client.post(
        "/api/backtest",
        content='{"ticker": "AAPL", "start_date": "2023-01-01", "end_date": "2024-01-01", "initial_capital": NaN}',
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_malformed_ticker_symbols_rejected_not_crashed(api_client):
    for bad_ticker in ["<script>alert(1)</script>", "'; DROP TABLE users; --", "A" * 500, "😀😀😀"]:
        resp = api_client.get(f"/api/stock/{bad_ticker}")
        assert resp.status_code in (400, 404, 422), f"unexpected status for {bad_ticker!r}: {resp.status_code}"
        assert "Traceback" not in resp.text


def test_massive_date_range_does_not_crash(api_client):
    resp = api_client.post(
        "/api/backtest",
        json={"ticker": "AAPL", "start_date": "1900-01-01", "end_date": "2026-01-01"},
    )
    # Either a clean validation error or a clean (if slow) real computation -
    # never a 500 or a hung connection.
    assert resp.status_code in (200, 400, 404, 422, 429, 503)
