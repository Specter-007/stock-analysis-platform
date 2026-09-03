"""API-level tests. Network I/O (yfinance) is monkeypatched at the
`app.services.market_data` boundary so these tests are fast and
deterministic - only the HTTP/schema layer and error mapping are under
test here. Real-network integration tests live in
test_integration_real_data.py.
"""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import market_data
from app.services.exceptions import TickerNotFoundError
from app.services.market_data import ChartHistoryResult, DataMeta


def _synthetic_df(n=400, seed=42):
    rng = np.random.default_rng(seed)
    log_returns = rng.normal(loc=0.0004, scale=0.015, size=n)
    close = 100.0 * np.exp(np.cumsum(log_returns))
    open_ = np.empty(n)
    open_[0] = 100.0
    open_[1:] = close[:-1]
    noise = rng.uniform(0.001, 0.01, size=n)
    high = np.maximum(open_, close) * (1 + noise)
    low = np.minimum(open_, close) * (1 - noise)
    volume = rng.integers(1_000_000, 10_000_000, size=n).astype(float)
    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=index)


@pytest.fixture
def client(monkeypatch):
    df = _synthetic_df()

    def fake_full_history(ticker):
        return df, DataMeta(data_status="HISTORICAL", timeframe="Daily")

    def fake_chart_history(ticker, range_key):
        return ChartHistoryResult(full_df=df, visible_df=df.tail(30), meta=DataMeta(data_status="HISTORICAL", timeframe="Daily"), is_daily=True)

    def fake_overview(ticker):
        overview = {
            "ticker": ticker,
            "company_name": "Test Corp",
            "exchange": "NMS",
            "currency": "USD",
            "sector": "Technology",
            "industry": "Software",
            "last_price": float(df["Close"].iloc[-1]),
            "previous_close": float(df["Close"].iloc[-2]),
            "change": 1.0,
            "change_percent": 1.0,
            "day_high": float(df["High"].iloc[-1]),
            "day_low": float(df["Low"].iloc[-1]),
            "fifty_two_week_high": float(df["High"].max()),
            "fifty_two_week_low": float(df["Low"].min()),
            "market_cap": 1_000_000_000.0,
            "volume": float(df["Volume"].iloc[-1]),
            "average_volume": float(df["Volume"].mean()),
            "website": "https://example.com",
            "description": "A test company.",
        }
        return overview, DataMeta(data_status="DELAYED", timeframe="Real-time quote (delayed)")

    def fake_ticker_not_found(ticker):
        raise TickerNotFoundError(ticker)

    monkeypatch.setattr(market_data, "get_full_daily_history", fake_full_history)
    monkeypatch.setattr(market_data, "get_chart_history", fake_chart_history)
    monkeypatch.setattr(market_data, "get_overview", fake_overview)

    return TestClient(app)


def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_stock_overview_response_shape(client):
    resp = client.get("/api/stock/AAPL")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "AAPL"
    assert "data" in body and "meta" in body
    assert body["meta"]["data_source"] == "Yahoo Finance via yfinance"
    assert body["meta"]["data_status"] in ("LIVE", "DELAYED", "MARKET_CLOSED", "HISTORICAL", "UNAVAILABLE")


def test_ticker_lowercase_is_normalized(client):
    resp = client.get("/api/stock/aapl")
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "AAPL"


def test_invalid_ticker_returns_400(client):
    resp = client.get("/api/stock/" + "X" * 20)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_type"] == "INVALID_TICKER"
    assert "Traceback" not in body["detail"]


def test_history_response_has_candles_and_meta(client):
    resp = client.get("/api/stock/AAPL/history?range=1M")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["candles"]) > 0
    assert body["is_daily"] is True
    assert "date" in body["candles"][0]
    assert "close" in body["candles"][0]


def test_technical_response_has_all_categories(client):
    resp = client.get("/api/stock/AAPL/technical")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("trend", "momentum", "volatility", "volume", "price_relationships"):
        assert key in body
        assert len(body[key]) > 0
        for indicator in body[key]:
            assert set(("key", "label", "value", "interpretation", "status")) <= set(indicator.keys())


def test_signal_response_has_timeframe_and_freshness_fields(client):
    resp = client.get("/api/stock/AAPL/signal")
    assert resp.status_code == 200
    body = resp.json()
    assert body["signal"] in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
    assert 0 <= body["score"] <= 100
    assert 0 <= body["confidence"]["confidence_percent"] <= 100
    assert body["signal_timeframe"] == "Daily"
    assert "signal_generated_at" in body
    assert "latest_candle_date" in body
    assert "disclaimer" in body
    assert "guarantee" not in body["disclaimer"].lower() or "does not guarantee" in body["disclaimer"].lower()


def test_signal_disclaimer_present_and_honest(client):
    resp = client.get("/api/stock/AAPL/signal")
    disclaimer = resp.json()["disclaimer"].lower()
    forbidden_phrases = ["guaranteed profit", "100% accurate", "risk-free", "certain winner"]
    for phrase in forbidden_phrases:
        assert phrase not in disclaimer


def test_ticker_not_found_returns_404(client, monkeypatch):
    monkeypatch.setattr(market_data, "get_overview", lambda t: (_ for _ in ()).throw(TickerNotFoundError(t)))
    resp = client.get("/api/stock/ZZZNOPE")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_type"] == "TICKER_NOT_FOUND"
    assert "Traceback" not in body["detail"]


def test_backtest_request_validates_date_order(client):
    resp = client.post(
        "/api/backtest",
        json={
            "ticker": "AAPL",
            "start_date": "2024-01-01",
            "end_date": "2023-01-01",
            "initial_capital": 10000,
        },
    )
    assert resp.status_code == 422


def test_backtest_rejects_non_daily_timeframe(client):
    resp = client.post(
        "/api/backtest",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "timeframe": "Weekly",
        },
    )
    assert resp.status_code == 422


def test_backtest_end_to_end_with_mocked_data(client):
    df = _synthetic_df()
    start = str(df.index[220].date())
    end = str(df.index[-1].date())
    resp = client.post(
        "/api/backtest",
        json={
            "ticker": "AAPL",
            "start_date": start,
            "end_date": end,
            "initial_capital": 10000,
            "transaction_cost_bps": 5,
            "slippage_bps": 5,
            "benchmark_ticker": None,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["initial_capital"] == 10000
    assert "methodology" in body
    assert "no_look_ahead" in body["methodology"]
    assert len(body["strategy_curve"]) > 0
    assert len(body["warnings"]) >= 0
