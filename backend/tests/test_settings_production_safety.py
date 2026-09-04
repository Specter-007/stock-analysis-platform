"""Production-safety checks in app.settings: the app must refuse to start
rather than silently run with an insecure configuration when
APP_ENV=production. These import the module fresh in a subprocess-like
isolated way (importlib.reload after monkeypatching env vars) since
app.settings performs its validation at import time.
"""
import importlib
import sys

import pytest


def _reload_settings():
    sys.modules.pop("app.settings", None)
    return importlib.import_module("app.settings")


@pytest.fixture(autouse=True)
def _restore_settings_module():
    yield
    # Always leave a normal (non-production) app.settings imported for every
    # other test module that runs after this file, regardless of outcome.
    for key in (
        "APP_ENV", "SESSION_SECRET", "CORS_ALLOWED_ORIGINS", "EMAIL_PROVIDER",
        "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD",
    ):
        import os

        os.environ.pop(key, None)
    _reload_settings()


def test_production_refuses_insecure_default_session_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.com")
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        _reload_settings()


def test_production_refuses_missing_cors_origins(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "a-real-secret")
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    with pytest.raises(RuntimeError, match="CORS_ALLOWED_ORIGINS"):
        _reload_settings()


def test_production_refuses_wildcard_cors_origin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "a-real-secret")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="CORS_ALLOWED_ORIGINS"):
        _reload_settings()


def test_production_refuses_smtp_without_credentials(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "a-real-secret")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.com")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    with pytest.raises(RuntimeError, match="EMAIL_PROVIDER=smtp"):
        _reload_settings()


def test_production_starts_with_complete_valid_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "a-real-secret")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.com")
    settings = _reload_settings()
    assert settings.IS_PRODUCTION is True
    assert settings.CORS_ALLOWED_ORIGINS == ["https://example.com"]


def test_development_allows_insecure_defaults(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    settings = _reload_settings()  # must not raise
    assert settings.IS_PRODUCTION is False
