"""app.rate_limit's storage backend selection (see Phase 4 of the
navbar/deployment-prep hardening pass): in-memory by default (correct for a
single-process deployment), optionally redis:// for a shared multi-process/
multi-instance backend, and - critically - fail-safe if that backend is
unreachable rather than turning every request into a 500.
"""
import importlib
import sys

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address


def _reload_rate_limit():
    sys.modules.pop("app.settings", None)
    sys.modules.pop("app.rate_limit", None)
    return importlib.import_module("app.rate_limit")


@pytest.fixture(autouse=True)
def _restore():
    # app.rate_limit.limiter is a process-wide singleton: app.main and every
    # route module hold a reference to whichever object existed when *they*
    # were first imported. Reloading the module for this test must not leave
    # a *different* object in sys.modules afterward, or conftest.py's
    # `from app.rate_limit import limiter` (used to reset the limiter
    # between other tests) would silently start resetting a orphaned
    # duplicate instead of the one actually wired into the app - starving
    # every other test file's rate limits. Save and restore the exact
    # original module objects instead of just deleting them.
    original_settings = sys.modules.get("app.settings")
    original_rate_limit = sys.modules.get("app.rate_limit")
    yield
    if original_settings is not None:
        sys.modules["app.settings"] = original_settings
    else:
        sys.modules.pop("app.settings", None)
    if original_rate_limit is not None:
        sys.modules["app.rate_limit"] = original_rate_limit
    else:
        sys.modules.pop("app.rate_limit", None)


def test_defaults_to_in_memory_storage_when_unconfigured(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_STORAGE_URL", raising=False)
    rate_limit = _reload_rate_limit()

    from limits.storage.memory import MemoryStorage

    assert isinstance(rate_limit.limiter._storage, MemoryStorage)


def test_uses_redis_storage_when_configured(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URL", "redis://localhost:6399/0")
    rate_limit = _reload_rate_limit()

    from limits.storage.redis import RedisStorage

    # Construction is lazy (redis-py doesn't connect until first command) -
    # this proves the configured backend is actually wired in, without
    # requiring a real Redis server in the test environment.
    assert isinstance(rate_limit.limiter._storage, RedisStorage)


def test_in_memory_fallback_is_enabled_only_when_a_shared_backend_is_configured(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_STORAGE_URL", raising=False)
    rate_limit = _reload_rate_limit()
    assert rate_limit.limiter._in_memory_fallback_enabled is False

    monkeypatch.setenv("RATE_LIMIT_STORAGE_URL", "redis://localhost:6399/0")
    rate_limit = _reload_rate_limit()
    assert rate_limit.limiter._in_memory_fallback_enabled is True


def test_unreachable_redis_backend_falls_back_to_in_memory_limiting_instead_of_500ing():
    """The critical "fail safely" property: an unreachable/misconfigured
    RATE_LIMIT_STORAGE_URL must never turn every request into a 500 - it
    must transparently keep enforcing limits on a per-process basis instead.
    Port 1 is never a real Redis server, so every storage operation fails.
    """
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="redis://localhost:1/0",
        in_memory_fallback_enabled=True,
        in_memory_fallback=["3/minute"],
    )
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/ping")
    @limiter.limit("3/minute")
    def ping(request: Request):
        return {"ok": True}

    client = TestClient(app)
    statuses = [client.get("/ping").status_code for _ in range(6)]

    assert all(s in (200, 429) for s in statuses), statuses
    assert 200 in statuses
    assert 429 in statuses, "expected the in-memory fallback limit to still be enforced"
