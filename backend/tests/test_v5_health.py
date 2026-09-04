"""V5: health endpoint reports persistence status without ever calling
Yahoo Finance - a health check that depends on an external network call
would make an unrelated data-provider outage look like this service itself
is down.
"""
import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok_status():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model_version"]


def test_health_reports_persistence_for_every_data_store():
    resp = client.get("/api/health")
    body = resp.json()
    assert set(body["persistence"].keys()) == {"paper_trading", "watchlists", "experiments"}
    assert all(v == "ok" for v in body["persistence"].values())


def test_health_never_mentions_a_live_data_fetch():
    resp = client.get("/api/health")
    body = resp.json()
    assert "not checked" in body["data_service"]


def test_health_is_fast():
    start = time.monotonic()
    client.get("/api/health")
    elapsed = time.monotonic() - start
    assert elapsed < 1.0  # a real yfinance call would take vastly longer
