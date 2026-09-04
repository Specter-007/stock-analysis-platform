"""Genuine PostgreSQL validation - not SQLite compatibility mode.

Docker is not available in this environment (checked: `docker` is not on
PATH). Instead this uses `pgserver` (https://pypi.org/project/pgserver/),
a pip-installable package that bundles a real, disposable PostgreSQL
server binary - no system-wide install, no admin rights, fully local and
removable (`pip uninstall pgserver`). This is a genuine PostgreSQL 16
server, not a mock or a SQLite-in-Postgres-clothing shim.

If pgserver is not installed, or the server genuinely cannot start in the
current environment, every test in this module is SKIPPED with an
explicit "NOT VERIFIED - real PostgreSQL unavailable" reason - never
silently reported as passing.

Two genuine environment/tooling bugs were found and worked around while
building this validation (documented, not silently papered over):

1. `pgserver.get_server()`'s default `initdb` invocation crashes
   (STATUS_STACK_BUFFER_OVERRUN) on this machine because the Windows
   system locale is Turkish - a real, reproducible bug in this PostgreSQL
   Windows build's locale handling, unrelated to this application. Passing
   `--locale=C` to `initdb` explicitly (not exposed by pgserver's
   high-level API, so invoked directly here) avoids it.
2. `subprocess.run([pg_ctl, ..., "start"], capture_output=True)` hangs
   forever on Windows: `pg_ctl start` launches a detached `postgres.exe`
   server that inherits the captured stdout/stderr pipe handles, so the
   pipe's read end never sees EOF even after `pg_ctl` itself has long
   since exited successfully - `subprocess.run` blocks waiting for a
   close that will never come until the (deliberately long-lived) server
   process also exits. Fixed by redirecting `pg_ctl`'s own stdout/stderr
   to `DEVNULL` instead of capturing them (the server's actual output
   already goes to `-l <logfile>`, which is read directly on failure).

This is why this file manages the server process directly instead of
calling `pgserver.get_server()`.
"""
from __future__ import annotations

import shutil
import socket
import subprocess
import uuid
from pathlib import Path

import pytest

pgserver = pytest.importorskip(
    "pgserver", reason="NOT VERIFIED - pgserver is not installed; real PostgreSQL validation skipped, not faked."
)

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

_PG_BIN = Path(pgserver.__file__).parent / "pginstall" / "bin"
_IS_WINDOWS = _PG_BIN.joinpath("initdb.exe").exists()
_INITDB = str(_PG_BIN / ("initdb.exe" if _IS_WINDOWS else "initdb"))
_PG_CTL = str(_PG_BIN / ("pg_ctl.exe" if _IS_WINDOWS else "pg_ctl"))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def real_postgres(tmp_path_factory):
    pgdata = tmp_path_factory.mktemp("pg_validation_data")
    port = _free_port()

    try:
        init = subprocess.run(
            [_INITDB, "-D", str(pgdata), "--auth=trust", "--auth-local=trust", "--encoding=utf8", "-U", "postgres", "--locale=C"],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        pytest.skip("NOT VERIFIED - real PostgreSQL unavailable in this environment (initdb timed out).")
    if init.returncode != 0:
        pytest.skip(f"NOT VERIFIED - real PostgreSQL unavailable in this environment (initdb failed): {init.stderr[-800:]}")

    log_path = pgdata.parent / "pg_validation_server.log"
    # stdout/stderr are DEVNULL, not captured: pg_ctl start launches a
    # detached, long-lived postgres.exe that inherits captured pipe
    # handles on Windows, which then never sees EOF - see the module
    # docstring's bug #2. The server's real output goes to `-l log_path`.
    try:
        start = subprocess.run(
            [_PG_CTL, "-D", str(pgdata), "-l", str(log_path), "-o", f"-p {port} -c listen_addresses=127.0.0.1", "start"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60,
        )
    except subprocess.TimeoutExpired:
        pytest.skip("NOT VERIFIED - real PostgreSQL unavailable in this environment (pg_ctl start timed out).")
    if start.returncode != 0:
        log_tail = log_path.read_text(errors="replace")[-800:] if log_path.exists() else "(no log file)"
        pytest.skip(f"NOT VERIFIED - real PostgreSQL unavailable in this environment (server start failed): {log_tail}")

    try:
        yield {"port": port, "base_uri": f"postgresql+psycopg2://postgres@127.0.0.1:{port}/postgres"}
    finally:
        subprocess.run(
            [_PG_CTL, "-D", str(pgdata), "stop", "-m", "immediate"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
        )
        shutil.rmtree(pgdata, ignore_errors=True)


@pytest.fixture
def pg_session(real_postgres):
    """A fresh, uniquely-named real PostgreSQL database per test - genuine
    test isolation without reusing tables/rows across tests, unlike simply
    pointing the whole existing SQLite-oriented suite at one shared
    Postgres database (which would cross-contaminate unique constraints
    like user email across unrelated tests)."""
    db_name = f"pgtest_{uuid.uuid4().hex[:16]}"
    admin_engine = create_engine(real_postgres["base_uri"], isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    db_url = f"postgresql+psycopg2://postgres@127.0.0.1:{real_postgres['port']}/{db_name}"
    engine = create_engine(db_url)

    import app.models_db  # noqa: F401
    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        admin_engine2 = create_engine(real_postgres["base_uri"], isolation_level="AUTOCOMMIT")
        with admin_engine2.connect() as conn:
            conn.execute(text(f'DROP DATABASE "{db_name}" WITH (FORCE)'))
        admin_engine2.dispose()


def _make_user(db, email="a@example.com"):
    from app.models_db.user import User

    user = User(email=email, password_hash="x", display_name="Test")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------- Schema

def test_connection_and_server_version(real_postgres):
    engine = create_engine(real_postgres["base_uri"])
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
    engine.dispose()
    assert "PostgreSQL" in version


def test_all_tables_created(pg_session):
    rows = pg_session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    ).fetchall()
    names = {r[0] for r in rows}
    assert names == {
        "users", "user_preferences", "user_sessions", "auth_tokens", "notifications",
        "support_requests", "watchlists", "paper_portfolios", "experiments",
    }


def test_json_columns_are_real_jsonb(pg_session):
    rows = pg_session.execute(
        text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='experiments'")
    ).fetchall()
    types = dict(rows)
    assert types["config"] == "jsonb"
    assert types["results"] == "jsonb"
    assert types["tags"] == "jsonb"


def test_foreign_keys_have_expected_delete_behavior(pg_session):
    rows = pg_session.execute(
        text(
            "SELECT conrelid::regclass::text, confdeltype FROM pg_constraint "
            "WHERE contype='f' AND confrelid = 'users'::regclass"
        )
    ).fetchall()
    behavior = dict(rows)
    for cascading_table in ("watchlists", "paper_portfolios", "experiments", "notifications", "user_sessions", "auth_tokens", "user_preferences"):
        assert behavior[cascading_table] == "c", f"{cascading_table} should CASCADE"
    assert behavior["support_requests"] == "n", "support_requests should SET NULL"


def test_unique_constraints_enforced(pg_session):
    from app.models_db.watchlist import WatchlistDB

    user = _make_user(pg_session)
    pg_session.add(WatchlistDB(user_id=user.id, slug="default", tickers=[]))
    pg_session.commit()
    pg_session.add(WatchlistDB(user_id=user.id, slug="default", tickers=[]))
    with pytest.raises(IntegrityError):
        pg_session.commit()


# ------------------------------------------------------------- Cascades

def test_cascade_delete_removes_every_owned_row(pg_session):
    from app.models_db.experiment import ExperimentDB
    from app.models_db.notification import Notification
    from app.models_db.paper_trading import PaperPortfolioDB
    from app.models_db.session import UserSession
    from app.models_db.user import UserPreferences
    from app.models_db.watchlist import WatchlistDB

    user = _make_user(pg_session)
    pg_session.add(UserPreferences(user_id=user.id))
    pg_session.add(UserSession(user_id=user.id, token_hash="h" * 64, expires_at=user.created_at))
    pg_session.add(WatchlistDB(user_id=user.id, slug="default", tickers=["AAPL"]))
    pg_session.add(PaperPortfolioDB(user_id=user.id, slug="default", state={"cash": 1000}))
    pg_session.add(
        ExperimentDB(
            id="exp_realpg000001", user_id=user.id, name="t", status="DRAFT",
            fingerprint="AAAA-BBBB-CCCC-DDDD", config={}, results={},
            created_at="2026-01-01T00:00:00+00:00", updated_at="2026-01-01T00:00:00+00:00",
        )
    )
    pg_session.add(Notification(user_id=user.id, type="SYSTEM", title="t", message="m"))
    pg_session.commit()

    pg_session.delete(user)
    pg_session.commit()

    assert pg_session.query(UserPreferences).count() == 0
    assert pg_session.query(UserSession).count() == 0
    assert pg_session.query(WatchlistDB).count() == 0
    assert pg_session.query(PaperPortfolioDB).count() == 0
    assert pg_session.query(ExperimentDB).count() == 0
    assert pg_session.query(Notification).count() == 0


def test_support_request_survives_deletion_with_null_user(pg_session):
    from app.models_db.support import SupportRequest

    user = _make_user(pg_session)
    pg_session.add(SupportRequest(user_id=user.id, contact_email=user.email, category="BUG", subject="s", message="m"))
    pg_session.commit()

    pg_session.delete(user)
    pg_session.commit()

    remaining = pg_session.query(SupportRequest).all()
    assert len(remaining) == 1
    assert remaining[0].user_id is None


# --------------------------------------------------------- Transactions

def test_rollback_discards_uncommitted_changes(pg_session):
    from app.models_db.user import User

    user = _make_user(pg_session)
    pg_session.add(User(email="uncommitted@example.com", password_hash="x", display_name="Ghost"))
    pg_session.rollback()

    assert pg_session.query(User).filter_by(email="uncommitted@example.com").count() == 0
    # The original commit before the rollback attempt is unaffected.
    assert pg_session.query(User).filter_by(id=user.id).count() == 1


def test_json_field_round_trips_nested_structures(pg_session):
    from app.models_db.experiment import ExperimentDB

    user = _make_user(pg_session)
    nested_config = {
        "tickers": ["AAPL", "MSFT"],
        "portfolio_constraints": {"max_position_percent": 20.0, "sector_caps": {"Technology": 0.4}},
        "sensitivity_parameters": ["buy_threshold", "sell_threshold"],
    }
    row = ExperimentDB(
        id="exp_realpg000002", user_id=user.id, name="t", status="DRAFT",
        fingerprint="AAAA-BBBB-CCCC-EEEE", config=nested_config, results={"backtest": {"nested": [1, 2, 3]}},
        created_at="2026-01-01T00:00:00+00:00", updated_at="2026-01-01T00:00:00+00:00",
    )
    pg_session.add(row)
    pg_session.commit()
    pg_session.expire_all()

    reloaded = pg_session.get(ExperimentDB, "exp_realpg000002")
    assert reloaded.config["portfolio_constraints"]["sector_caps"]["Technology"] == 0.4
    assert reloaded.results["backtest"]["nested"] == [1, 2, 3]


def test_naive_utc_timestamp_round_trips_without_tz_errors(pg_session):
    """The exact bug class this schema's naive-UTC convention exists to
    avoid (see app/db/timeutil.py) - verify it doesn't resurface against a
    real PostgreSQL server, which (unlike SQLite) DOES have a native
    timezone-aware type, to make sure the naive convention is honored
    consistently rather than PostgreSQL silently upgrading it."""
    from datetime import datetime, timezone

    from app.db.timeutil import utcnow_naive
    from app.models_db.session import UserSession

    user = _make_user(pg_session)
    session_row = UserSession(user_id=user.id, token_hash="h" * 64, expires_at=utcnow_naive())
    pg_session.add(session_row)
    pg_session.commit()
    pg_session.expire_all()

    reloaded = pg_session.get(UserSession, session_row.id)
    assert reloaded.expires_at.tzinfo is None
    # Must not raise "can't compare offset-naive and offset-aware datetimes".
    assert reloaded.expires_at <= utcnow_naive()
    with pytest.raises(TypeError):
        reloaded.expires_at <= datetime.now(timezone.utc)  # proves the column really is naive, not silently tz-aware


# -------------------------------------------------- Multi-user isolation

def test_two_users_each_own_default_slug_without_collision(pg_session):
    from app.models_db.watchlist import WatchlistDB

    user_a = _make_user(pg_session, "a@example.com")
    user_b = _make_user(pg_session, "b@example.com")
    pg_session.add(WatchlistDB(user_id=user_a.id, slug="default", tickers=["AAPL"]))
    pg_session.add(WatchlistDB(user_id=user_b.id, slug="default", tickers=["TSLA"]))
    pg_session.commit()  # must not raise

    assert pg_session.query(WatchlistDB).count() == 2


def test_real_service_layer_register_and_own_data_is_isolated(pg_session):
    """Exercises the actual application service functions (not just raw
    ORM inserts) against real PostgreSQL: register two real users via
    app.auth.service, give each their own watchlist/paper-portfolio/
    experiment through the real store modules, and confirm cross-user
    lookups return nothing - the same IDOR-prevention pattern verified
    against SQLite in test_idor.py, now proven against Postgres too."""
    from app.auth import service as auth_service
    from app.experiments import store as experiments_store
    from app.experiments.models import ExperimentConfig
    from app.paper_trading import store as paper_trading_store
    from app.watchlist import store as watchlist_store

    user_a = auth_service.register(pg_session, email="pg-a@example.com", password="abc12345", display_name="A")
    user_b = auth_service.register(pg_session, email="pg-b@example.com", password="abc12345", display_name="B")

    watchlist_store.save_tickers(pg_session, user_a.id, "default", ["AAPL"])
    paper_trading_store.save_portfolio(pg_session, user_a.id, "default", {"cash": 9000, "positions": {}, "trades": []})

    from app.experiments.fingerprint import compute_fingerprint
    from app.experiments.models import Experiment

    config = ExperimentConfig(
        model_version="1.1", tickers=["AAPL"], benchmark="SPY", start_date="2023-01-01",
        end_date="2024-01-01", initial_capital=10000.0, commission_bps=5.0, slippage_bps=5.0,
    )
    experiment = Experiment(
        id=experiments_store.new_experiment_id(), name="Real PG test", created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00", status="DRAFT", config=config, fingerprint=compute_fingerprint(config),
    )
    experiments_store.save_experiment(pg_session, user_a.id, experiment)

    # User B sees none of it.
    assert watchlist_store.load_tickers(pg_session, user_b.id, "default") == []
    assert paper_trading_store.load_portfolio(pg_session, user_b.id, "default")["cash"] == 10_000.0  # fresh default
    assert experiments_store.load_experiment(pg_session, user_b.id, experiment.id) is None

    # User A sees their own data correctly.
    assert watchlist_store.load_tickers(pg_session, user_a.id, "default") == ["AAPL"]
    assert experiments_store.load_experiment(pg_session, user_a.id, experiment.id) is not None


def test_account_deletion_cascades_through_real_service_layer(pg_session):
    from app.auth import service as auth_service
    from app.models_db.watchlist import WatchlistDB
    from app.watchlist import store as watchlist_store

    user = auth_service.register(pg_session, email="pg-delete@example.com", password="abc12345", display_name="D")
    watchlist_store.save_tickers(pg_session, user.id, "default", ["AAPL"])

    auth_service.delete_account(pg_session, user)

    assert auth_service.get_user_by_id(pg_session, user.id) is None
    assert pg_session.query(WatchlistDB).count() == 0


# ------------------------------------------------------------ Notifications

def test_notification_persistence_against_real_postgres(pg_session):
    from app.notifications import service as notifications_service
    from app.models_db.notification import TYPE_SYSTEM

    user = _make_user(pg_session)
    notifications_service.create_notification(pg_session, user.id, TYPE_SYSTEM, "Title", "Body")
    assert notifications_service.unread_count(pg_session, user.id) == 1


# ------------------------------------------------------------- Concurrency

def test_sequential_sessions_do_not_lose_updates(real_postgres, pg_session):
    """A simple, real concurrency sanity check: two separate SQLAlchemy
    sessions (simulating two separate request-handling workers) against
    the SAME database, each committing an update - the second commit must
    see the first session's already-committed row, not a stale copy."""
    from sqlalchemy.orm import sessionmaker

    from app.models_db.paper_trading import PaperPortfolioDB

    user = _make_user(pg_session)
    pg_session.add(PaperPortfolioDB(user_id=user.id, slug="default", state={"cash": 10000}))
    pg_session.commit()

    engine = pg_session.get_bind()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    session_1 = SessionLocal()
    session_2 = SessionLocal()
    try:
        row_1 = session_1.query(PaperPortfolioDB).filter_by(user_id=user.id, slug="default").one()
        row_1.state = {"cash": 9000}
        session_1.commit()

        row_2 = session_2.query(PaperPortfolioDB).filter_by(user_id=user.id, slug="default").one()
        assert row_2.state["cash"] == 9000  # session_2 sees session_1's committed write, not a stale cached value
    finally:
        session_1.close()
        session_2.close()


def test_duplicate_slug_race_is_rejected_not_silently_lost(pg_session):
    """Two 'requests' racing to create the same (user, slug) watchlist must
    result in exactly one row and a real constraint violation for the
    loser - never two rows, never a silently-overwritten one."""
    from sqlalchemy.orm import sessionmaker

    from app.models_db.watchlist import WatchlistDB

    user = _make_user(pg_session)
    engine = pg_session.get_bind()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    session_1 = SessionLocal()
    session_2 = SessionLocal()
    try:
        session_1.add(WatchlistDB(user_id=user.id, slug="race", tickers=["AAPL"]))
        session_1.commit()

        session_2.add(WatchlistDB(user_id=user.id, slug="race", tickers=["TSLA"]))
        with pytest.raises(IntegrityError):
            session_2.commit()
        session_2.rollback()

        assert pg_session.query(WatchlistDB).filter_by(user_id=user.id, slug="race").count() == 1
    finally:
        session_1.close()
        session_2.close()
