"""Shared deterministic synthetic fixtures.

IMPORTANT: this synthetic data exists only to test calculation logic in
isolation. It must never be used as a fallback for real production market
data anywhere in the application - see app/services/market_data.py, which
only ever returns data actually retrieved from Yahoo Finance.
"""
import numpy as np
import pandas as pd
import pytest


def _make_ohlcv(n: int, seed: int, start_price: float = 100.0, drift: float = 0.0005, vol: float = 0.015) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    log_returns = rng.normal(loc=drift, scale=vol, size=n)
    close = start_price * np.exp(np.cumsum(log_returns))

    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1]

    intraday_noise = rng.uniform(0.001, 0.01, size=n)
    high = np.maximum(open_, close) * (1 + intraday_noise)
    low = np.minimum(open_, close) * (1 - intraday_noise)
    volume = rng.integers(1_000_000, 10_000_000, size=n).astype(float)

    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=index,
    )


@pytest.fixture
def ohlcv_long():
    """400 business days - enough for every indicator window (SMA 200 included)."""
    return _make_ohlcv(400, seed=42)


@pytest.fixture
def ohlcv_short():
    """10 business days - not enough for most indicators."""
    return _make_ohlcv(10, seed=7)


@pytest.fixture
def ohlcv_uptrend():
    """Strong, low-noise uptrend so trend/momentum factors are unambiguous."""
    return _make_ohlcv(400, seed=1, drift=0.004, vol=0.006)


@pytest.fixture
def ohlcv_downtrend():
    """Strong, low-noise downtrend."""
    return _make_ohlcv(400, seed=2, drift=-0.004, vol=0.006)


@pytest.fixture
def ohlcv_high_volatility():
    return _make_ohlcv(400, seed=3, drift=0.0, vol=0.06)


def _make_test_engine():
    """A single-connection (StaticPool) in-memory SQLite engine - required
    (not just SingletonThreadPool, SQLAlchemy's own default for ':memory:')
    because FastAPI's TestClient dispatches sync endpoints to a worker
    thread pool, so different requests in the same test can land on
    different threads; StaticPool guarantees they all still see the same
    in-memory database instead of each getting its own empty one."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.pool import StaticPool

    import app.models_db  # noqa: F401  (registers every model on Base.metadata)
    from app.db.base import Base

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session():
    """An isolated, fresh in-memory SQLite database for a single test -
    exercises the exact same SQLAlchemy models/constraints the production
    PostgreSQL schema uses (see app/db/base.py for the portability notes).
    """
    from sqlalchemy.orm import sessionmaker

    engine = _make_test_engine()
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def api_client():
    """A TestClient wired to its own isolated in-memory database (via a
    FastAPI dependency override of app.db.base.get_db) and a reset rate
    limiter, for exercising the real HTTP auth/authorization layer end to
    end - as opposed to `db_session`, which talks to the ORM directly.
    """
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.db.base import get_db
    from app.main import app
    from app.rate_limit import limiter

    engine = _make_test_engine()
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    limiter.reset()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def register_and_login(client, email: str, password: str = "abc12345", display_name: str = "Test User"):
    """Shared helper: registers + logs in a user against `api_client`,
    returning (user_body, csrf_token) - the client keeps the session/CSRF
    cookies from the response for subsequent requests."""
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": display_name, "accept_terms": True},
    )
    assert resp.status_code == 201, resp.text
    csrf_token = client.cookies.get("csrf_token")
    return resp.json(), csrf_token
