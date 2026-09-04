"""SQLAlchemy engine/session setup.

Production target is PostgreSQL (see docs/DATABASE.md). The engine is
selected entirely from the DATABASE_URL environment variable so the exact
same ORM models and Alembic migrations run unchanged against either
backend:

  - Production:        postgresql+psycopg2://user:pass@host:5432/dbname
  - Local dev/test:     sqlite:///./data/app.db   (this repo's default)

Honesty note: this development environment does not have a PostgreSQL
server installed. All ORM models, migrations, and tests in this codebase
have been designed to be dialect-portable (see `app.db.types.portable_json`
for the one place - JSON columns - where PostgreSQL and SQLite genuinely
differ) and have been verified against SQLite here. They have NOT been
verified against a real running PostgreSQL instance in this environment.
Before production use, point DATABASE_URL at a real PostgreSQL server and
re-run `alembic upgrade head` plus the test suite against it.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DEFAULT_SQLITE_PATH = Path("data") / "app.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}")

_is_sqlite = DATABASE_URL.startswith("sqlite")
_connect_args: dict = {}
if _is_sqlite:
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency yielding a request-scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    """Create tables directly from ORM metadata.

    Used by the test suite (fast, no Alembic dependency) and as a
    convenience for first-run local dev. Production schema changes must go
    through Alembic migrations (see docs/DATABASE.md) - this function is
    never invoked from application startup code.
    """
    import app.models_db  # noqa: F401  (ensures every model is registered on Base.metadata)

    Base.metadata.create_all(bind=engine)
