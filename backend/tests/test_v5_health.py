"""V5/SaaS: health (liveness) never calls Yahoo Finance or the database -
a health check that depends on an external dependency would make an
unrelated outage look like this service itself is down. Readiness
additionally confirms the database is reachable, for deployment
orchestrators deciding whether to route traffic to this instance.
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


def test_health_never_mentions_a_live_data_fetch():
    resp = client.get("/api/health")
    body = resp.json()
    assert "not checked" in body["data_service"]


def test_health_has_no_database_key():
    """Liveness is deliberately DB-free - that's what /api/health/ready is for."""
    resp = client.get("/api/health")
    assert "database" not in resp.json()


def test_health_is_fast():
    start = time.monotonic()
    client.get("/api/health")
    elapsed = time.monotonic() - start
    assert elapsed < 1.0  # a real yfinance or DB call would take vastly longer than this


def test_readiness_reports_database_ok():
    resp = client.get("/api/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_readiness_reports_error_without_crashing_when_db_unavailable(monkeypatch):
    from app.db.base import get_db

    def broken_db():
        class _Broken:
            def execute(self, *_args, **_kwargs):
                raise RuntimeError("simulated database outage")

        yield _Broken()

    app.dependency_overrides[get_db] = broken_db
    try:
        resp = client.get("/api/health/ready")
        assert resp.status_code == 200  # the probe itself must never 500
        body = resp.json()
        assert body["status"] == "not_ready"
        assert "simulated database outage" in body["database"]
    finally:
        app.dependency_overrides.pop(get_db, None)
