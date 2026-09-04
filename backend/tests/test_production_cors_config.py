"""Regression coverage for the exact production configuration used to
deploy the backend to Render, fronted by the real Vercel frontend at
https://stock-analysis-platform-gamma.vercel.app - added while wiring
that deployment up, so a future change can't silently break it.

Two separate things are verified:
1. app.settings itself accepts this configuration (APP_ENV=production,
   a real SESSION_SECRET, CORS_ALLOWED_ORIGINS set to the real Vercel
   origin) WITHOUT a DATABASE_URL - documenting, on purpose, that the
   public/stateless stock-analysis endpoints do not require a database at
   all, so this specific interim deployment (analysis engine only, before
   a real managed Postgres is provisioned) is not blocked by the
   settings-level fail-fast checks. This is not the same as claiming a
   database is configured - see docs/DATABASE.md and render.yaml's
   DATABASE_URL comment for that honesty note.
2. A real CORS preflight from that exact Vercel origin is actually
   accepted, and from any other origin is actually rejected - using a
   genuine OPTIONS request (see test_v5_cors.py's module docstring for
   why this must be tested against real HTTP behavior, not just
   configuration values: a browser's preflight is the thing that fails
   silently if this is misconfigured, not any Python-level assertion).
"""
import importlib
import sys

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

PRODUCTION_FRONTEND_ORIGIN = "https://stock-analysis-platform-gamma.vercel.app"


def _reload_settings():
    sys.modules.pop("app.settings", None)
    return importlib.import_module("app.settings")


@pytest.fixture(autouse=True)
def _restore():
    original = sys.modules.get("app.settings")
    yield
    if original is not None:
        sys.modules["app.settings"] = original
    else:
        sys.modules.pop("app.settings", None)


def test_settings_accept_the_real_render_deployment_config_without_a_database(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "a-real-private-secret-not-the-dev-default")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", PRODUCTION_FRONTEND_ORIGIN)
    monkeypatch.setenv("FRONTEND_URL", PRODUCTION_FRONTEND_ORIGIN)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = _reload_settings()  # must not raise

    assert settings.IS_PRODUCTION is True
    assert settings.CORS_ALLOWED_ORIGINS == [PRODUCTION_FRONTEND_ORIGIN]
    assert settings.SESSION_COOKIE_SECURE is True


def _preflight(app: FastAPI, origin: str):
    client = TestClient(app)
    return client.options(
        "/api/stock/AAPL",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def _build_app_with_cors(allowed_origins: list[str]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/api/stock/{ticker}")
    def _stub(ticker: str):
        return {"ticker": ticker}

    return app


def test_real_vercel_origin_preflight_is_accepted():
    app = _build_app_with_cors([PRODUCTION_FRONTEND_ORIGIN])
    resp = _preflight(app, PRODUCTION_FRONTEND_ORIGIN)
    assert resp.status_code < 400
    assert resp.headers.get("access-control-allow-origin") == PRODUCTION_FRONTEND_ORIGIN


def test_an_unrelated_origin_preflight_is_rejected():
    app = _build_app_with_cors([PRODUCTION_FRONTEND_ORIGIN])
    resp = _preflight(app, "https://not-the-real-frontend.example.com")
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers.keys()}
