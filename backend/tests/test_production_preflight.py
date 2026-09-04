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
    # app.db.base holds process-wide singletons (engine, Base, the get_db
    # dependency function conftest.py's api_client fixture keys its
    # dependency override off of) - popping it during a test to force a
    # fresh DATABASE_URL (for the migration-status checks below) must not
    # leave a *different* module object behind afterward, the same lesson
    # learned fixing test_rate_limit_storage.py's fixture.
    original_db_base = sys.modules.get("app.db.base")
    yield
    sys.modules.pop("app.settings", None)
    sys.modules.pop("production_preflight", None)
    if original_db_base is not None:
        sys.modules["app.db.base"] = original_db_base
    else:
        sys.modules.pop("app.db.base", None)


def test_preflight_fails_fast_on_missing_production_secret(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    preflight = _reload_settings_and_preflight()
    assert preflight.main() == 1


def test_preflight_fails_on_missing_database_url_in_production(monkeypatch, capsys):
    """Documents a real, deliberate deployment decision (see render.yaml):
    the backend can and does boot under APP_ENV=production with no
    DATABASE_URL at all - the public stock-analysis endpoints never touch
    the database - but preflight must still call this out as a FAIL, not
    silently accept a SQLite fallback as production-ready. This is an
    accepted, documented gap for that specific interim deployment, not a
    hidden one."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "a-real-secret")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://stock-analysis-platform-gamma.vercel.app")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    preflight = _reload_settings_and_preflight()
    exit_code = preflight.main()
    out = capsys.readouterr().out
    assert "[FAIL] DATABASE_URL" in out
    assert exit_code == 1


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
    from alembic import command
    from alembic.config import Config

    db_path = tmp_path / "preflight_test.db"
    db_url = f"sqlite:///{db_path.as_posix()}"

    # alembic/env.py deliberately ignores whatever URL is passed to the
    # Config object and instead imports DATABASE_URL from app.db.base (so
    # `alembic upgrade head` always targets whatever the app itself is
    # configured for) - so DATABASE_URL must be set, and app.db.base
    # popped so it re-imports with this value, *before* running the
    # upgrade, or it silently migrates the wrong (real dev) database.
    monkeypatch.setenv("DATABASE_URL", db_url)
    sys.modules.pop("app.db.base", None)

    # A "complete, valid" production config includes an actually-migrated
    # database - preflight's migration-status check (see
    # test_preflight_fails_on_unmigrated_database below) would otherwise
    # correctly FAIL on a fresh, never-migrated database, which is real and
    # desired behavior, not something this test should paper over.
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "a-real-secret")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "1")
    preflight = _reload_settings_and_preflight()
    exit_code = preflight.main()
    out = capsys.readouterr().out
    assert "[FAIL]" not in out
    assert exit_code == 0


def test_preflight_fails_on_unmigrated_database(monkeypatch, capsys, tmp_path):
    """A database that exists and is reachable but has never had `alembic
    upgrade head` run against it must FAIL, not silently pass - the app
    cannot actually serve traffic against it."""
    db_path = tmp_path / "unmigrated.db"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "a-real-secret")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "1")
    preflight = _reload_settings_and_preflight()
    exit_code = preflight.main()
    out = capsys.readouterr().out
    assert "[FAIL] Migration status" in out
    assert exit_code == 1


def test_preflight_warns_but_does_not_fail_on_unreachable_rate_limit_storage(monkeypatch, capsys):
    """RATE_LIMIT_STORAGE_URL is optional infrastructure the app already
    fails open on (see app/rate_limit.py's in_memory_fallback_enabled) - an
    unreachable one should be surfaced, but must not block a deployment
    that doesn't actually need it to be reachable."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URL", "redis://localhost:1/0")
    preflight = _reload_settings_and_preflight()
    exit_code = preflight.main()
    out = capsys.readouterr().out
    assert "[WARN] RATE_LIMIT_STORAGE_URL" in out
    assert "[FAIL] RATE_LIMIT_STORAGE_URL" not in out
    assert exit_code == 0
