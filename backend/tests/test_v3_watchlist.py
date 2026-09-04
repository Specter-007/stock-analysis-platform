"""Tests for the watchlist: CRUD backed by an isolated in-memory database
(see the `db_session` fixture in conftest.py), with enrichment mocked to
avoid network calls. Every watchlist is owned by a real user row - see
test_watchlists_of_different_users_are_isolated for the IDOR-prevention
check (two different users each get their own "default" watchlist).
"""
import pytest

from app.watchlist import service as watchlist_service
from app.watchlist import store as watchlist_store


@pytest.fixture
def user_id(db_session):
    from app.models_db.user import User

    user = User(email="watchlist-test@example.com", password_hash="x", display_name="Test")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user.id


def test_new_watchlist_is_empty(db_session, user_id):
    result = watchlist_service.get_watchlist(db_session, user_id, "wl1")
    assert result.tickers == []
    assert result.entries == []


def test_add_ticker_persists(db_session, user_id):
    watchlist_service.add_ticker(db_session, user_id, "wl2", "aapl")
    tickers = watchlist_store.load_tickers(db_session, user_id, "wl2")
    assert tickers == ["AAPL"]


def test_add_duplicate_ticker_is_idempotent(db_session, user_id):
    watchlist_service.add_ticker(db_session, user_id, "wl3", "AAPL")
    watchlist_service.add_ticker(db_session, user_id, "wl3", "aapl")
    assert watchlist_store.load_tickers(db_session, user_id, "wl3") == ["AAPL"]


def test_remove_ticker(db_session, user_id):
    watchlist_service.add_ticker(db_session, user_id, "wl4", "AAPL")
    watchlist_service.add_ticker(db_session, user_id, "wl4", "MSFT")
    watchlist_service.remove_ticker(db_session, user_id, "wl4", "AAPL")
    assert watchlist_store.load_tickers(db_session, user_id, "wl4") == ["MSFT"]


def test_add_invalid_ticker_rejected(db_session, user_id):
    with pytest.raises(Exception):
        watchlist_service.add_ticker(db_session, user_id, "wl5", "###")


def test_max_watchlist_size_enforced(monkeypatch, db_session, user_id):
    monkeypatch.setattr(watchlist_service, "MAX_WATCHLIST_SIZE", 2)
    watchlist_service.add_ticker(db_session, user_id, "wl6", "AAPL")
    watchlist_service.add_ticker(db_session, user_id, "wl6", "MSFT")
    with pytest.raises(watchlist_service.WatchlistError):
        watchlist_service.add_ticker(db_session, user_id, "wl6", "NVDA")


def test_watchlists_are_isolated_by_slug(db_session, user_id):
    watchlist_service.add_ticker(db_session, user_id, "alice_wl", "AAPL")
    bob = watchlist_service.get_watchlist(db_session, user_id, "bob_wl")
    assert bob.tickers == []


def test_watchlists_of_different_users_are_isolated(db_session, user_id):
    from app.models_db.user import User

    other = User(email="watchlist-other@example.com", password_hash="x", display_name="Other")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    watchlist_service.add_ticker(db_session, user_id, "default", "AAPL")
    watchlist_service.add_ticker(db_session, other.id, "default", "TSLA")

    mine = watchlist_service.get_watchlist(db_session, user_id, "default")
    theirs = watchlist_service.get_watchlist(db_session, other.id, "default")
    assert mine.tickers == ["AAPL"]
    assert theirs.tickers == ["TSLA"]


def test_get_watchlist_enriches_each_ticker(monkeypatch, db_session, user_id):
    watchlist_service.add_ticker(db_session, user_id, "wl7", "AAPL")
    watchlist_service.add_ticker(db_session, user_id, "wl7", "MSFT")

    def fake_enrich(ticker, regime):
        return watchlist_service.WatchlistEntry(
            ticker=ticker, company_name=f"{ticker} Inc.", price=100.0, change_percent=1.0,
            signal="BUY", score=70.0, trend_classification="Bullish", market_regime=regime,
            data_status="DELAYED", signal_changed_today=False,
        )

    monkeypatch.setattr(watchlist_service, "_enrich", fake_enrich)
    monkeypatch.setattr(watchlist_service.market_data, "get_full_daily_history", lambda t: (_ for _ in ()).throw(RuntimeError("not used")))

    result = watchlist_service.get_watchlist(db_session, user_id, "wl7")
    assert len(result.entries) == 2
    assert {e.ticker for e in result.entries} == {"AAPL", "MSFT"}
    assert all(e.signal == "BUY" for e in result.entries)


def test_get_watchlist_degrades_gracefully_when_ticker_fails(monkeypatch, db_session, user_id):
    watchlist_service.add_ticker(db_session, user_id, "wl8", "AAPL")

    def failing_enrich(ticker, regime):
        return watchlist_service.WatchlistEntry(
            ticker=ticker, company_name=None, price=None, change_percent=None,
            signal=None, score=None, trend_classification=None, market_regime=None,
            data_status="UNAVAILABLE", signal_changed_today=False, error="boom",
        )

    monkeypatch.setattr(watchlist_service, "_enrich", failing_enrich)
    result = watchlist_service.get_watchlist(db_session, user_id, "wl8")
    assert result.entries[0].error == "boom"
    assert result.entries[0].data_status == "UNAVAILABLE"
