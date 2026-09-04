"""Centralized environment-derived configuration for the production SaaS
foundation (auth, sessions, CORS, email, rate limiting).

Every value is read from an environment variable with a documented,
clearly-non-production default so local dev/test needs no setup. When
APP_ENV=production, the values that MUST be explicitly configured are
validated at import time and the app refuses to start with an insecure
default - see docs/DEPLOYMENT.md and .env.example.

Quant-engine constants (indicator windows, score thresholds, etc.) remain
in app.config - this module is only for deployment/environment concerns.
"""
from __future__ import annotations

import os

APP_ENV = os.environ.get("APP_ENV", "development")  # development | test | production
IS_PRODUCTION = APP_ENV == "production"

# --- Session secret (signs CSRF tokens - see app.auth.security) ---
_INSECURE_DEFAULT_SESSION_SECRET = "dev-insecure-session-secret-change-me"
SESSION_SECRET = os.environ.get("SESSION_SECRET", _INSECURE_DEFAULT_SESSION_SECRET)
if IS_PRODUCTION and SESSION_SECRET == _INSECURE_DEFAULT_SESSION_SECRET:
    raise RuntimeError(
        "SESSION_SECRET must be set to a real, private secret when APP_ENV=production. "
        "Refusing to start with the insecure development default."
    )

# --- Session cookie ---
SESSION_COOKIE_NAME = "session_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
SESSION_TTL_DAYS = int(os.environ.get("SESSION_TTL_DAYS", "30"))
# Secure requires HTTPS - only forced on in production. Local dev over
# plain http would silently drop the cookie if this were always True.
SESSION_COOKIE_SECURE = IS_PRODUCTION or os.environ.get("SESSION_COOKIE_SECURE") == "1"

# --- CORS (existing app.main.py env var, kept for backward compatibility) ---
_default_origins = "http://localhost:3000,http://127.0.0.1:3000" if not IS_PRODUCTION else ""
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()
]
if IS_PRODUCTION and not CORS_ALLOWED_ORIGINS:
    raise RuntimeError("CORS_ALLOWED_ORIGINS must be set (comma-separated) when APP_ENV=production.")
if IS_PRODUCTION and "*" in CORS_ALLOWED_ORIGINS:
    raise RuntimeError("CORS_ALLOWED_ORIGINS may not contain '*' when APP_ENV=production (credentialed CORS).")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# --- Email (provider-agnostic - see app.auth.email) ---
# "console": logs the email content instead of sending it - safe for local
# dev/test, never used to claim a real email was sent (see app.auth.email).
EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "console")
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
EMAIL_FROM_ADDRESS = os.environ.get("EMAIL_FROM_ADDRESS", "no-reply@localhost")
if IS_PRODUCTION and EMAIL_PROVIDER == "smtp" and not (SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD):
    raise RuntimeError("EMAIL_PROVIDER=smtp requires SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD to be set.")

# --- Logging ---
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# --- Rate limiting (see app.rate_limit) ---
RATE_LIMIT_AUTH = os.environ.get("RATE_LIMIT_AUTH", "5/minute")
RATE_LIMIT_PASSWORD_RESET = os.environ.get("RATE_LIMIT_PASSWORD_RESET", "3/minute")
RATE_LIMIT_CONTACT = os.environ.get("RATE_LIMIT_CONTACT", "3/minute")
RATE_LIMIT_EXPENSIVE_RESEARCH = os.environ.get("RATE_LIMIT_EXPENSIVE_RESEARCH", "20/minute")

# --- Legacy JSON -> Postgres migration ownership (see scripts/migrate_json_to_db.py) ---
LEGACY_DATA_OWNER_EMAIL = os.environ.get("LEGACY_DATA_OWNER_EMAIL", "legacy-import@localhost")
