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
