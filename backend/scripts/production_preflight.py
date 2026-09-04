#!/usr/bin/env python
"""Production preflight check - run before starting the backend in a real
production deployment (not invoked automatically by the app itself).

Validates the environment configuration app.settings itself enforces at
import time, plus a few things that are import-time-safe to *not* hard-fail
on (so this script can report them as warnings even in a dev run) but that
matter for a real launch: SMTP configuration, and reachability of the
configured database.

Never prints a secret value - only whether one is set and non-default.

Usage:
    cd backend
    python scripts/production_preflight.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_PASS = "[PASS]"
_WARN = "[WARN]"
_FAIL = "[FAIL]"

_results: list[tuple[str, str]] = []


def _check(label: str, ok: bool, detail: str, *, warn_only: bool = False) -> None:
    status = _PASS if ok else (_WARN if warn_only else _FAIL)
    _results.append((status, f"{label}: {detail}"))


def main() -> int:
    print("=== Production preflight ===\n")

    app_env = os.environ.get("APP_ENV", "development")
    _check("APP_ENV", app_env == "production", f"{app_env!r} (must be 'production' for a real launch)", warn_only=(app_env != "production"))

    # Importing app.settings performs its own fail-fast validation (raises
    # RuntimeError) for SESSION_SECRET / CORS_ALLOWED_ORIGINS when
    # APP_ENV=production - if that succeeds, those checks already passed.
    try:
        import app.settings as settings  # noqa: E402

        _check("SESSION_SECRET", True, "set to a non-default value" if settings.SESSION_SECRET != "dev-insecure-session-secret-change-me" else "using the DEV placeholder - insecure for production", warn_only=(settings.SESSION_SECRET == "dev-insecure-session-secret-change-me" and not settings.IS_PRODUCTION))
        _check(
            "CORS_ALLOWED_ORIGINS", bool(settings.CORS_ALLOWED_ORIGINS) and "*" not in settings.CORS_ALLOWED_ORIGINS,
            f"{len(settings.CORS_ALLOWED_ORIGINS)} explicit origin(s) configured" if settings.CORS_ALLOWED_ORIGINS else "not set",
        )
    except RuntimeError as exc:
        # app.settings itself refused to import under APP_ENV=production -
        # this IS the fail-fast behavior working as intended.
        print(f"{_FAIL} app.settings refused to load: {exc}\n")
        return 1

    database_url = os.environ.get("DATABASE_URL")
    _check("DATABASE_URL", bool(database_url), "set" if database_url else "not set - will default to a local SQLite file, not suitable for production", warn_only=not settings.IS_PRODUCTION)

    engine = None
    if database_url:
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _check("Database connectivity", True, "connected and responded to SELECT 1")
        except Exception as exc:  # noqa: BLE001
            _check("Database connectivity", False, f"could not connect: {exc}")
            engine = None
    else:
        _check("Database connectivity", False, "skipped - DATABASE_URL not set", warn_only=True)

    if engine is not None:
        try:
            from alembic.config import Config
            from alembic.runtime.migration import MigrationContext
            from alembic.script import ScriptDirectory

            backend_dir = Path(__file__).resolve().parent.parent
            alembic_cfg = Config(str(backend_dir / "alembic.ini"))
            alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
            script = ScriptDirectory.from_config(alembic_cfg)
            repo_heads = set(script.get_heads())

            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                db_heads = set(context.get_current_heads())

            if not db_heads:
                _check("Migration status", False, "no migrations have been applied to this database - run `alembic upgrade head` before starting the app")
            elif db_heads == repo_heads:
                _check("Migration status", True, f"up to date (head: {', '.join(sorted(db_heads))})")
            else:
                _check(
                    "Migration status", False,
                    f"database is at {sorted(db_heads)} but the repo's latest is {sorted(repo_heads)} - run `alembic upgrade head`",
                )
        except Exception as exc:  # noqa: BLE001
            _check("Migration status", False, f"could not determine migration status: {exc}", warn_only=True)
        finally:
            engine.dispose()

    _check(
        "EMAIL_PROVIDER", settings.EMAIL_PROVIDER == "smtp",
        f"{settings.EMAIL_PROVIDER!r}" + (" - verification/reset emails will only be logged, never delivered" if settings.EMAIL_PROVIDER != "smtp" else " - real delivery configured"),
        warn_only=True,
    )
    if settings.EMAIL_PROVIDER == "smtp":
        smtp_ok = bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)
        _check("SMTP credentials", smtp_ok, "all present" if smtp_ok else "incomplete")

    if settings.RATE_LIMIT_STORAGE_URL:
        try:
            from limits.storage import storage_from_string

            storage = storage_from_string(settings.RATE_LIMIT_STORAGE_URL, socket_connect_timeout=2, socket_timeout=2)
            reachable = storage.check()
            _check(
                "RATE_LIMIT_STORAGE_URL", reachable,
                "reachable - rate limits shared across processes" if reachable else
                "configured but unreachable - the app will still run correctly, falling back to per-process limiting",
                warn_only=not reachable,
            )
        except Exception as exc:  # noqa: BLE001
            _check("RATE_LIMIT_STORAGE_URL", False, f"configured but could not be checked: {exc} - falls back to per-process limiting", warn_only=True)
    else:
        _check("RATE_LIMIT_STORAGE_URL", True, "not set - rate limiting is per-process only (fine for a single instance)", warn_only=True)

    _check("FRONTEND_URL", bool(settings.FRONTEND_URL), settings.FRONTEND_URL)
    _check("SESSION_COOKIE_SECURE", settings.SESSION_COOKIE_SECURE, "enabled" if settings.SESSION_COOKIE_SECURE else "disabled (fine for local HTTP dev, must be enabled in production)", warn_only=not settings.IS_PRODUCTION)

    print()
    any_fail = False
    for status, message in _results:
        print(f"{status} {message}")
        if status == _FAIL:
            any_fail = True

    print()
    if any_fail:
        print("Preflight FAILED - do not deploy with the configuration above.")
        return 1
    if any(status == _WARN for status, _ in _results):
        print("Preflight passed with warnings - review them before a real launch.")
        return 0
    print("Preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
