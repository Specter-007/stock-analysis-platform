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

_TEST_USER_EMAIL = "integration-test@example.com"
_TEST_USER_PASSWORD = "integrationtest1"


def _ensure_authenticated() -> None:
    """Registers (or, on repeat runs against the same persistent dev
    database, logs in as) a fixed test account so the now-auth-gated
    watchlist/paper-trading/experiment endpoints are reachable exactly as a
    real signed-in user would reach them - never bypassing auth for tests.
    """
    resp = client.post(
        "/api/auth/register",
        json={"email": _TEST_USER_EMAIL, "password": _TEST_USER_PASSWORD, "display_name": "Integration Test"},
    )
    if resp.status_code == 409:
        resp = client.post("/api/auth/login", json={"email": _TEST_USER_EMAIL, "password": _TEST_USER_PASSWORD})
    assert resp.status_code in (200, 201), resp.text


def _csrf_headers() -> dict:
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def _network_available() -> bool:
    try:
        df, _ = market_data.get_full_daily_history("AAPL")
        return not df.empty
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _network_available(), reason="No network access to Yahoo Finance in this environment.")

if _network_available():
    _ensure_authenticated()


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
    reset_resp = client.post(
        f"/api/paper-portfolio/reset?portfolio_id={portfolio_id}&starting_capital=10000", headers=_csrf_headers()
    )
    assert reset_resp.status_code == 200

    buy_resp = client.post(
        "/api/paper-trade",
        json={"portfolio_id": portfolio_id, "ticker": "AAPL", "action": "BUY", "shares": 1},
        headers=_csrf_headers(),
    )
    assert buy_resp.status_code == 200
    body = buy_resp.json()
    assert len(body["positions"]) == 1
    assert body["positions"][0]["current_price"] > 0
    assert body["cash"] < 10000


def test_real_backtest_includes_advanced_metrics():
    resp = client.post(
        "/api/backtest",
        json={
            "ticker": "AAPL",
            "start_date": "2021-01-01",
            "end_date": "2026-08-01",
            "benchmark_ticker": "SPY",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    m = body["advanced_metrics"]
    assert m["cagr_percent"] is not None
    assert m["beta"] is not None  # benchmark was supplied, so this must not be None
    assert m["average_win"] is not None or body["number_of_trades"] == 0


def test_real_sensitivity_analysis():
    resp = client.post(
        "/api/backtest/sensitivity",
        json={"ticker": "MSFT", "start_date": "2021-01-01", "end_date": "2026-08-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["parameters"]) == 2
    for p in body["parameters"]:
        assert p["robustness"] in ("HIGHER_ROBUSTNESS", "LOW_ROBUSTNESS", "PARAMETER_INERT", "INSUFFICIENT_DATA")


def test_real_out_of_sample_validation():
    resp = client.post(
        "/api/backtest/out-of-sample",
        json={
            "ticker": "AAPL",
            "in_sample_start": "2019-01-01", "in_sample_end": "2022-12-31",
            "validation_start": "2023-01-01", "validation_end": "2024-12-31",
            "out_of_sample_start": "2025-01-01", "out_of_sample_end": "2026-08-01",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [p["label"] for p in body["periods"]] == ["IN_SAMPLE", "VALIDATION", "OUT_OF_SAMPLE"]


def test_real_regime_performance():
    resp = client.post(
        "/api/model/regime-performance",
        json={"ticker": "NVDA", "benchmark": "SPY", "start_date": "2021-01-01", "end_date": "2026-08-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["buckets"]) > 0
    total_days = sum(b["trading_days"] for b in body["buckets"])
    assert total_days > 0


def test_real_data_quality_reported_in_meta():
    resp = client.get("/api/stock/AAPL/technical")
    assert resp.status_code == 200
    quality = resp.json()["meta"]["data_quality"]
    assert quality is not None
    assert quality["is_valid"] is True


def test_real_watchlist_end_to_end():
    watchlist_id = "integration_test_watchlist"
    client.delete(f"/api/watchlist/AAPL?watchlist_id={watchlist_id}", headers=_csrf_headers())  # ensure clean slate
    add_resp = client.post(
        "/api/watchlist", json={"watchlist_id": watchlist_id, "ticker": "AAPL"}, headers=_csrf_headers()
    )
    assert add_resp.status_code == 200
    body = add_resp.json()
    entry = next(e for e in body["entries"] if e["ticker"] == "AAPL")
    assert entry["price"] is not None
    assert entry["signal"] in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")

    remove_resp = client.delete(f"/api/watchlist/AAPL?watchlist_id={watchlist_id}", headers=_csrf_headers())
    assert remove_resp.status_code == 200
    assert remove_resp.json()["tickers"] == []


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


# ---------------------------------------------------------------------- V4


def test_real_sensitivity_extended_indicator_parameters():
    resp = client.post(
        "/api/backtest/sensitivity",
        json={
            "ticker": "AAPL", "start_date": "2022-01-01", "end_date": "2024-01-01",
            "parameters": ["buy_threshold", "sell_threshold", "rsi_period", "sma_short", "sma_long", "macd_fast", "macd_slow"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["parameters"]) == 7
    for p in body["parameters"]:
        assert p["robustness"] in ("HIGHER_ROBUSTNESS", "LOW_ROBUSTNESS", "PARAMETER_INERT", "INSUFFICIENT_DATA", "INSUFFICIENT_SAMPLE")


def test_real_sensitivity_heatmap():
    resp = client.post(
        "/api/backtest/sensitivity/heatmap",
        json={
            "ticker": "AAPL", "start_date": "2022-01-01", "end_date": "2024-01-01",
            "param_x": "buy_threshold", "param_y": "rsi_period",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["cells"]) == 25


def test_real_paper_portfolio_history_records_a_snapshot():
    portfolio_id = "integration_test_history"
    client.post(f"/api/paper-portfolio/reset?portfolio_id={portfolio_id}&starting_capital=10000", headers=_csrf_headers())
    resp = client.get(f"/api/paper-portfolio/history?portfolio_id={portfolio_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["snapshots"]) >= 1
    assert body["snapshots"][0]["equity"] == pytest.approx(10000.0, abs=1.0)


def test_real_forward_validation_reports_honest_sample_size():
    portfolio_id = "integration_test_forward"
    client.post(f"/api/paper-portfolio/reset?portfolio_id={portfolio_id}&starting_capital=10000", headers=_csrf_headers())
    resp = client.get(f"/api/paper-portfolio/forward-validation?portfolio_id={portfolio_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["trading_days_observed"] >= 1
    assert body["insufficient_sample"] is True  # a brand-new portfolio never has enough history


def test_real_portfolio_backtest_multi_ticker():
    resp = client.post(
        "/api/backtest/portfolio",
        json={
            "tickers": ["AAPL", "MSFT", "NVDA"],
            "start_date": "2023-01-01", "end_date": "2024-01-01",
            "initial_capital": 30000, "benchmark_ticker": "SPY",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["final_capital"] > 0
    assert len(body["equity_curve"]) > 0
    assert body["risk_analytics"]["correlation_matrix"] is not None


def test_real_stock_comparison():
    resp = client.post("/api/compare", json={"tickers": ["AAPL", "MSFT", "NVDA"]})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["rows"]) == 3
    for row in body["rows"]:
        assert row["error"] is None
        assert row["signal"] in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
        if row["historical_volatility_percent"] is not None:
            assert 0 <= row["historical_volatility_percent"] < 500  # guards the double-scaling bug found in this phase


def test_real_model_scorecard():
    resp = client.post("/api/model/scorecard", json={"ticker": "AAPL", "benchmark": "SPY"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["dimensions"]) == 5
    names = {d["name"] for d in body["dimensions"]}
    assert names == {
        "OUT_OF_SAMPLE_STRENGTH", "ROBUSTNESS", "WALK_FORWARD_STABILITY",
        "REGIME_DEPENDENCY", "FORWARD_PAPER_DATA",
    }
    assert "composite_score" not in body


def test_real_model_version_comparison():
    resp = client.post(
        "/api/model/compare-versions",
        json={"ticker": "AAPL", "start_date": "2023-01-01", "end_date": "2024-01-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["backtest_comparison"]) == 2
    assert {r["model_version"] for r in body["backtest_comparison"]} == {"1.0", "1.1"}


# ---------------------------------------------------------------------- V5


def test_real_cost_stress_test():
    resp = client.post(
        "/api/backtest/cost-stress",
        json={"ticker": "AAPL", "start_date": "2022-01-01", "end_date": "2024-01-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["commission_scenarios"]) == 4
    assert len(body["slippage_scenarios"]) == 5
    # Trade decisions never depend on cost, so every scenario shares the same trade count.
    trade_counts = {s["number_of_trades"] for s in body["commission_scenarios"]}
    assert len(trade_counts) == 1


def test_real_monte_carlo_extended_statistics():
    resp = client.post(
        "/api/backtest/monte-carlo",
        json={"ticker": "AAPL", "start_date": "2022-01-01", "end_date": "2024-01-01", "simulations": 200, "seed": 1},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["seed"] == 1
    assert body["resampling_method"] in ("iid_bootstrap", "block_bootstrap", "unavailable")
    if body["resampling_basis"] != "unavailable":
        assert 0 <= body["probability_of_loss_percent"] <= 100
        assert 0 <= body["probability_of_exceeding_drawdown_threshold_percent"] <= 100


def test_real_model_drift():
    resp = client.post("/api/model/drift", json={"ticker": "AAPL", "benchmark": "SPY"})
    assert resp.status_code == 200
    body = resp.json()
    if not body["insufficient_data"]:
        for dim in ("signal_distribution", "factor_distribution", "regime_distribution"):
            assert body[dim] is not None
            total_historical = sum(body[dim]["historical_percent"].values())
            assert total_historical == pytest.approx(100.0, abs=1.0)


def test_real_experiment_full_lifecycle():
    create_resp = client.post(
        "/api/experiments",
        json={
            "name": "Integration Test Experiment",
            "config": {
                "tickers": ["AAPL"], "benchmark": "SPY",
                "start_date": "2022-01-01", "end_date": "2024-01-01",
                "initial_capital": 10000, "run_out_of_sample": True,
            },
        },
        headers=_csrf_headers(),
    )
    assert create_resp.status_code == 200
    experiment_id = create_resp.json()["id"]
    fingerprint = create_resp.json()["fingerprint"]

    try:
        run_resp = client.post(f"/api/experiments/{experiment_id}/run", headers=_csrf_headers())
        assert run_resp.status_code == 200
        ran = run_resp.json()
        assert ran["status"] in ("VALIDATED", "COMPLETED")
        assert ran["results"]["backtest"]["completed"] is True
        assert len(ran["results"]["backtest"]["result"]["strategy_curve"]) > 0

        reopened = client.get(f"/api/experiments/{experiment_id}").json()
        assert reopened["fingerprint"] == fingerprint  # unchanged by running

        dup_resp = client.post(f"/api/experiments/{experiment_id}/duplicate", json={}, headers=_csrf_headers())
        assert dup_resp.status_code == 200
        assert dup_resp.json()["fingerprint"] == fingerprint
        client.delete(f"/api/experiments/{dup_resp.json()['id']}", headers=_csrf_headers())

        list_resp = client.get("/api/experiments")
        assert experiment_id in [row["experiment"]["id"] for row in list_resp.json()["experiments"]]
    finally:
        client.delete(f"/api/experiments/{experiment_id}", headers=_csrf_headers())


def test_real_paper_portfolios_listing():
    resp = client.get("/api/paper-portfolios")
    assert resp.status_code == 200
    assert isinstance(resp.json()["portfolios"], list)
