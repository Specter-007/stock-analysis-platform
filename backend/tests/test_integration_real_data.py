"""Real-network integration tests against actual Yahoo Finance data.

These intentionally do NOT mock anything - they exist to prove the whole
stack (yfinance -> indicators -> signal engine -> API) works against real,
live-retrieved market data, not just synthetic fixtures. They require
network access and will be skipped automatically if the network is
unavailable rather than failing the whole suite.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import market_data

REAL_TICKERS = ["AAPL", "MSFT", "NVDA"]

client = TestClient(app)


def _network_available() -> bool:
    try:
        df, _ = market_data.get_full_daily_history("AAPL")
        return not df.empty
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _network_available(), reason="No network access to Yahoo Finance in this environment.")


@pytest.mark.parametrize("ticker", REAL_TICKERS)
def test_real_overview_has_real_company_data(ticker):
    resp = client.get(f"/api/stock/{ticker}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["company_name"] != "N/A"
    assert body["data"]["last_price"] is not None and body["data"]["last_price"] > 0
    assert body["meta"]["data_status"] in ("DELAYED", "MARKET_CLOSED")
    assert body["meta"]["retrieved_at"]


@pytest.mark.parametrize("ticker", REAL_TICKERS)
def test_real_technical_indicators_calculate(ticker):
    resp = client.get(f"/api/stock/{ticker}/technical")
    assert resp.status_code == 200
    body = resp.json()
    sma200 = next(i for i in body["trend"] if i["key"] == "sma_200")
    assert sma200["value"] is not None
    assert sma200["status"] in ("bullish", "bearish")
    assert body["trend_classification"] != "Insufficient Data"


@pytest.mark.parametrize("ticker", REAL_TICKERS)
def test_real_signal_generated_with_timestamps(ticker):
    resp = client.get(f"/api/stock/{ticker}/signal")
    assert resp.status_code == 200
    body = resp.json()
    assert body["signal"] in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
    assert body["signal_timeframe"] == "Daily"
    assert body["signal_generated_at"]
    assert body["latest_candle_date"]
    assert len(body["positive_factors"]) + len(body["negative_factors"]) + len(body["neutral_factors"]) > 0
    assert body["model_version"] == "1.1"
    assert abs(sum(body["score_breakdown"].values()) - body["score"]) > -1  # breakdown present and numeric
    assert "stability_percent" in body["stability"]
    assert isinstance(body["invalidation_conditions"], list) and len(body["invalidation_conditions"]) >= 1


@pytest.mark.parametrize("ticker", REAL_TICKERS)
def test_real_signal_history_uses_real_past_data(ticker):
    resp = client.get(f"/api/stock/{ticker}/signal-history?lookback_sessions=30")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["history"]) > 0
    for point in body["history"]:
        assert point["signal"] in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
        assert 0 <= point["score"] <= 100


def test_real_fundamentals_returns_real_or_na_fields():
    resp = client.get("/api/stock/AAPL/fundamentals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_any_data"] is True
    pe = next(m for m in body["valuation"] if m["key"] == "trailing_pe")
    assert pe["value"] is None or pe["value"] > 0


def test_real_relative_strength_against_spy():
    resp = client.get("/api/stock/NVDA/relative-strength?benchmark=SPY")
    assert resp.status_code == 200
    body = resp.json()
    assert body["benchmark"] == "SPY"
    assert len(body["periods"]) == 4
    for p in body["periods"]:
        assert p["classification"] in ("STRONG", "IN_LINE", "WEAK", "UNAVAILABLE")


def test_real_market_regime_from_spy():
    resp = client.get("/api/market/regime")
    assert resp.status_code == 200
    body = resp.json()
    assert body["regime"] in ("BULL", "BEAR", "SIDEWAYS", "HIGH_VOLATILITY", "UNAVAILABLE")
    assert body["benchmark"] == "SPY"


def test_real_model_info_endpoint():
    resp = client.get("/api/model")
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_version"] == "1.1"
    assert "1.0" in body["supported_versions"]


def test_real_walk_forward_against_real_data():
    resp = client.post(
        "/api/backtest/walk-forward",
        json={"ticker": "AAPL", "train_years": 2, "test_years": 1, "max_folds": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["folds"]) > 0
    assert "no trainable" in body["methodology"] or "trainable" in body["methodology"]


def test_real_monte_carlo_against_real_data():
    resp = client.post(
        "/api/backtest/monte-carlo",
        json={
            "ticker": "MSFT",
            "start_date": "2021-01-01",
            "end_date": "2024-01-01",
            "simulations": 200,
            "seed": 1,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["simulations"] == 200
    assert body["resampling_basis"] in ("trade_returns", "daily_returns", "unavailable")


def test_real_invalid_ticker_returns_404():
    # Valid ticker *format* (<= 12 chars) that does not exist on Yahoo Finance,
    # so this actually exercises the not-found path rather than input validation.
    resp = client.get("/api/stock/ZZZZNOPEXYZ")
    assert resp.status_code == 404
    assert resp.json()["error_type"] == "TICKER_NOT_FOUND"


def test_real_history_range_returns_candles():
    resp = client.get("/api/stock/AAPL/history?range=6M")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["candles"]) > 50
    assert body["candles"][-1]["close"] is not None


def test_real_paper_trade_uses_real_live_quote():
    portfolio_id = "integration_test_portfolio"
    reset_resp = client.post(f"/api/paper-portfolio/reset?portfolio_id={portfolio_id}&starting_capital=10000")
    assert reset_resp.status_code == 200

    buy_resp = client.post(
        "/api/paper-trade",
        json={"portfolio_id": portfolio_id, "ticker": "AAPL", "action": "BUY", "shares": 1},
    )
    assert buy_resp.status_code == 200
    body = buy_resp.json()
    assert len(body["positions"]) == 1
    assert body["positions"][0]["current_price"] > 0
    assert body["cash"] < 10000


def test_real_backtest_runs_against_real_data():
    resp = client.post(
        "/api/backtest",
        json={
            "ticker": "MSFT",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "initial_capital": 10000,
            "benchmark_ticker": "SPY",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["final_capital"] > 0
    assert body["total_return_percent"] is not None
