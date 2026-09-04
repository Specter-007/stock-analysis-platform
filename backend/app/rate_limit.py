"""Rate limiting via slowapi (in-memory limiter - see docs/DEPLOYMENT.md for
the documented single-process limitation: limits are per-worker-process,
not shared across a multi-process/multi-instance deployment, since adding
Redis here would be new infrastructure the app doesn't otherwise need).

Applied to: auth endpoints (register/login/password-reset/email-verify),
the contact form, and the most expensive research endpoints (Monte Carlo,
sensitivity, portfolio backtesting, comparison).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
