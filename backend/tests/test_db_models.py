"""SaaS foundation: SQLAlchemy model constraint/cascade tests.

These exercise the ORM layer directly against an in-memory SQLite database
(see the `db_session` fixture in conftest.py) - the same models and
constraints Alembic applies to the production PostgreSQL schema.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models_db import (
    ExperimentDB,
    Notification,
    PaperPortfolioDB,
    SupportRequest,
    User,
    UserPreferences,
    UserSession,
    WatchlistDB,
)


def _make_user(db_session, email="a@example.com"):
    user = User(email=email, password_hash="hashed", display_name="Alice")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_user_created_with_expected_defaults(db_session):
    user = _make_user(db_session)
    assert user.id
    assert user.role == "USER"
    assert user.is_active is True
    assert user.email_verified is False
    assert user.deleted_at is None


def test_duplicate_email_is_rejected(db_session):
    _make_user(db_session, email="dup@example.com")
    db_session.add(User(email="dup@example.com", password_hash="x", display_name="Bob"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_preferences_defaults(db_session):
    user = _make_user(db_session)
    prefs = UserPreferences(user_id=user.id)
    db_session.add(prefs)
    db_session.commit()
    db_session.refresh(prefs)
    assert prefs.timezone == "UTC"
    assert prefs.default_benchmark == "SPY"
    assert prefs.onboarding_completed is False
    assert prefs.marketing_consent is False


def test_deleting_user_cascades_to_owned_rows(db_session):
    user = _make_user(db_session)
    db_session.add(UserPreferences(user_id=user.id))
    db_session.add(UserSession(user_id=user.id, token_hash="h" * 64, expires_at=user.created_at))
    db_session.add(WatchlistDB(user_id=user.id, slug="default", tickers=["AAPL"]))
    db_session.add(PaperPortfolioDB(user_id=user.id, slug="default", state={"cash": 10000}))
    db_session.add(
        ExperimentDB(
            id="exp_deadbeef0001",
            user_id=user.id,
            name="test",
            status="DRAFT",
            fingerprint="AAAA-BBBB-CCCC-DDDD",
            config={},
            results={},
        )
    )
    db_session.add(Notification(user_id=user.id, type="SYSTEM", title="t", message="m"))
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    assert db_session.query(UserPreferences).count() == 0
    assert db_session.query(UserSession).count() == 0
    assert db_session.query(WatchlistDB).count() == 0
    assert db_session.query(PaperPortfolioDB).count() == 0
    assert db_session.query(ExperimentDB).count() == 0
    assert db_session.query(Notification).count() == 0


def test_deleting_user_nullifies_support_requests_instead_of_deleting_them(db_session):
    user = _make_user(db_session)
    db_session.add(
        SupportRequest(
            user_id=user.id, contact_email=user.email, category="BUG", subject="s", message="m"
        )
    )
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    remaining = db_session.query(SupportRequest).all()
    assert len(remaining) == 1
    assert remaining[0].user_id is None


def test_two_users_can_each_have_their_own_default_watchlist(db_session):
    user_a = _make_user(db_session, email="a@example.com")
    user_b = _make_user(db_session, email="b@example.com")
    db_session.add(WatchlistDB(user_id=user_a.id, slug="default", tickers=["AAPL"]))
    db_session.add(WatchlistDB(user_id=user_b.id, slug="default", tickers=["TSLA"]))
    db_session.commit()  # must not raise - uniqueness is scoped to (user_id, slug)
    assert db_session.query(WatchlistDB).count() == 2


def test_duplicate_slug_for_same_user_is_rejected(db_session):
    user = _make_user(db_session)
    db_session.add(WatchlistDB(user_id=user.id, slug="default", tickers=[]))
    db_session.commit()
    db_session.add(WatchlistDB(user_id=user.id, slug="default", tickers=[]))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_paper_portfolio_state_json_round_trips_nested_structure(db_session):
    user = _make_user(db_session)
    state = {
        "portfolio_id": "default",
        "cash": 8500.25,
        "positions": {"AAPL": {"shares": 10, "avg_cost": 150.0}},
        "trades": [{"ticker": "AAPL", "action": "BUY", "shares": 10}],
        "equity_snapshots": [],
        "benchmark_basis": None,
    }
    portfolio = PaperPortfolioDB(user_id=user.id, slug="default", state=state)
    db_session.add(portfolio)
    db_session.commit()
    db_session.refresh(portfolio)
    assert portfolio.state["positions"]["AAPL"]["shares"] == 10
    assert portfolio.state["trades"][0]["ticker"] == "AAPL"
