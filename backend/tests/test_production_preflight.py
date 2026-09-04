"""scripts/production_preflight.py - never prints secret values, fails
fast on a fundamentally broken production config, and passes (with
honest warnings) on a valid one.
"""
import importlib
import sys

import pytest


def _reload_settings_and_preflight():
    sys.modules.pop("app.settings", None)
    sys.modules.pop("scripts.production_preflight", None)
    sys.path.insert(0, "scripts")
    try:
        del sys.modules["production_preflight"]
    except KeyError:
        pass
    return importlib.import_module("production_preflight")


@pytest.fixture(autouse=True)
def _restore(monkeypatch):
    yield
    sys.modules.pop("app.settings", None)
    sys.modules.pop("production_preflight", None)


def test_preflight_fails_fast_on_missing_production_secret(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    preflight = _reload_settings_and_preflight()
    assert preflight.main() == 1
    out = capsys.readouterr().out
    assert "[FAIL]" in out


def test_preflight_never_prints_the_actual_secret_value(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "super-secret-value-must-not-leak")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.com")
    preflight = _reload_settings_and_preflight()
    preflight.main()
    out = capsys.readouterr().out
    assert "super-secret-value-must-not-leak" not in out


def test_preflight_passes_with_warnings_in_development(monkeypatch, capsys):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    preflight = _reload_settings_and_preflight()
    assert preflight.main() == 0
    out = capsys.readouterr().out
    assert "[WARN]" in out


def test_preflight_passes_cleanly_with_complete_valid_production_config(monkeypatch, capsys, tmp_path):
    db_path = tmp_path / "preflight_test.db"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "a-real-secret")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "1")
    preflight = _reload_settings_and_preflight()
    exit_code = preflight.main()
    out = capsys.readouterr().out
    assert "[FAIL]" not in out
    assert exit_code == 0
