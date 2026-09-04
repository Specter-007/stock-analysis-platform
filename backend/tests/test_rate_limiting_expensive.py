"""Rate limiting on the most expensive research endpoints (Monte Carlo,
sensitivity, sensitivity heatmap, portfolio backtest, comparison) and on
the email-verification-request endpoint - added during the final
production-hardening pass after auditing which endpoints in
app/settings.RATE_LIMIT_EXPENSIVE_RESEARCH's own docstring were not
actually decorated yet.

Each test spams the endpoint with a fast-failing (invalid ticker) payload
- slowapi's limiter counts every invocation attempt before the route body
runs, so a 422 from validation still counts against the limit, avoiding
any real yfinance calls in this test.
"""
from app.rate_limit import limiter


def _reset():
    limiter.reset()


def test_monte_carlo_endpoint_is_rate_limited(api_client):
    _reset()
    statuses = [
        api_client.post(
            "/api/backtest/monte-carlo",
            json={"ticker": "###", "start_date": "2023-01-01", "end_date": "2024-01-01"},
        ).status_code
        for _ in range(25)
    ]
    assert 429 in statuses


def test_sensitivity_endpoint_is_rate_limited(api_client):
    _reset()
    statuses = [
        api_client.post(
            "/api/backtest/sensitivity",
            json={"ticker": "###", "start_date": "2023-01-01", "end_date": "2024-01-01"},
        ).status_code
        for _ in range(25)
    ]
    assert 429 in statuses


def test_sensitivity_heatmap_endpoint_is_rate_limited(api_client):
    _reset()
    statuses = [
        api_client.post(
            "/api/backtest/sensitivity/heatmap",
            json={
                "ticker": "###", "start_date": "2023-01-01", "end_date": "2024-01-01",
                "param_x": "buy_threshold", "param_y": "rsi_period",
            },
        ).status_code
        for _ in range(25)
    ]
    assert 429 in statuses


def test_portfolio_backtest_endpoint_is_rate_limited(api_client):
    _reset()
    statuses = [
        api_client.post(
            "/api/backtest/portfolio",
            json={"tickers": ["###", "###2"], "start_date": "2023-01-01", "end_date": "2024-01-01"},
        ).status_code
        for _ in range(25)
    ]
    assert 429 in statuses


def test_compare_endpoint_is_rate_limited(api_client):
    _reset()
    statuses = [
        api_client.post("/api/compare", json={"tickers": ["###", "###2"]}).status_code
        for _ in range(25)
    ]
    assert 429 in statuses


def test_email_verification_request_endpoint_is_rate_limited(api_client):
    from tests.conftest import register_and_login

    _reset()
    register_and_login(api_client, "rate-limit-verify@example.com")
    statuses = [api_client.post("/api/auth/email-verification/request").status_code for _ in range(10)]
    assert 429 in statuses
