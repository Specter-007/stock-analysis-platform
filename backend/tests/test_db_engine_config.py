"""app.db.base's engine configuration: pool_pre_ping/pool_recycle are
enabled only for a real (non-SQLite) DATABASE_URL, so managed PostgreSQL
providers that silently close idle connections don't surface that as a
500 on the next request - and so local SQLite dev/test behavior (which
doesn't need or support these pool options meaningfully) is unaffected.
"""
import importlib
import sys

import pytest


def _reload_db_base():
    sys.modules.pop("app.db.base", None)
    return importlib.import_module("app.db.base")


@pytest.fixture(autouse=True)
def _restore():
    original = sys.modules.get("app.db.base")
    yield
    if original is not None:
        sys.modules["app.db.base"] = original
    else:
        sys.modules.pop("app.db.base", None)


def test_postgres_engine_enables_pre_ping_and_recycle(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@example-host:5432/stock_analyst")
    db_base = _reload_db_base()

    assert db_base.engine.pool._pre_ping is True
    assert db_base.engine.pool._recycle == 1800


def test_sqlite_engine_does_not_need_pre_ping(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    db_base = _reload_db_base()

    assert db_base.engine.pool._pre_ping is False
