"""Rate limiting via slowapi.

Storage backend: in-memory by default - limits are per-process, not shared
across a multi-process/multi-instance deployment (see docs/DEPLOYMENT.md).
Setting RATE_LIMIT_STORAGE_URL to a redis:// URL switches to a shared
backend so limits apply globally instead; if that backend is or becomes
unreachable, slowapi/limits' own in_memory_fallback_enabled transparently
falls back to per-process limiting instead of raising errors on every
request - this app doesn't need Redis to run correctly, so a broken/
misconfigured Redis must never take the whole API down.

Applied to: auth endpoints (register/login/password-reset/email-verify),
the contact form, and the most expensive research endpoints (Monte Carlo,
sensitivity, portfolio backtesting, comparison).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.settings import RATE_LIMIT_STORAGE_URL

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=RATE_LIMIT_STORAGE_URL or "memory://",
    in_memory_fallback_enabled=bool(RATE_LIMIT_STORAGE_URL),
)
