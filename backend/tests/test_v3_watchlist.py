"""Tests for the watchlist: CRUD backed by an isolated temp-directory store,
with enrichment mocked to avoid network calls.
"""
import pytest

from app.watchlist import service as watchlist_service
from app.watchlist import store as watchlist_store


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(watchlist_store, "_DATA_DIR", tmp_path / "watchlists")


def test_new_watchlist_is_empty():
    result = watchlist_service.get_watchlist("wl1")
    assert result.tickers == []
    assert result.entries == []


def test_add_ticker_persists():
    watchlist_service.add_ticker("wl2", "aapl")
    tickers = watchlist_store.load_tickers("wl2")
    assert tickers == ["AAPL"]


def test_add_duplicate_ticker_is_idempotent():
    watchlist_service.add_ticker("wl3", "AAPL")
    watchlist_service.add_ticker("wl3", "aapl")
    assert watchlist_store.load_tickers("wl3") == ["AAPL"]


def test_remove_ticker():
    watchlist_service.add_ticker("wl4", "AAPL")
    watchlist_service.add_ticker("wl4", "MSFT")
    watchlist_service.remove_ticker("wl4", "AAPL")
    assert watchlist_store.load_tickers("wl4") == ["MSFT"]


def test_add_invalid_ticker_rejected():
    with pytest.raises(Exception):
        watchlist_service.add_ticker("wl5", "###")


def test_max_watchlist_size_enforced(monkeypatch):
    monkeypatch.setattr(watchlist_service, "MAX_WATCHLIST_SIZE", 2)
    watchlist_service.add_ticker("wl6", "AAPL")
    watchlist_service.add_ticker("wl6", "MSFT")
    with pytest.raises(watchlist_service.WatchlistError):
        watchlist_service.add_ticker("wl6", "NVDA")


def test_watchlists_are_isolated_by_id():
    watchlist_service.add_ticker("alice_wl", "AAPL")
    bob = watchlist_service.get_watchlist("bob_wl")
    assert bob.tickers == []


def test_get_watchlist_enriches_each_ticker(monkeypatch):
    watchlist_service.add_ticker("wl7", "AAPL")
    watchlist_service.add_ticker("wl7", "MSFT")

    def fake_enrich(ticker, regime):
        return watchlist_service.WatchlistEntry(
            ticker=ticker, company_name=f"{ticker} Inc.", price=100.0, change_percent=1.0,
            signal="BUY", score=70.0, trend_classification="Bullish", market_regime=regime,
            data_status="DELAYED", signal_changed_today=False,
        )

    monkeypatch.setattr(watchlist_service, "_enrich", fake_enrich)
    monkeypatch.setattr(watchlist_service.market_data, "get_full_daily_history", lambda t: (_ for _ in ()).throw(RuntimeError("not used")))

    result = watchlist_service.get_watchlist("wl7")
    assert len(result.entries) == 2
    assert {e.ticker for e in result.entries} == {"AAPL", "MSFT"}
    assert all(e.signal == "BUY" for e in result.entries)


def test_get_watchlist_degrades_gracefully_when_ticker_fails(monkeypatch):
    watchlist_service.add_ticker("wl8", "AAPL")

    def failing_enrich(ticker, regime):
        return watchlist_service.WatchlistEntry(
            ticker=ticker, company_name=None, price=None, change_percent=None,
            signal=None, score=None, trend_classification=None, market_regime=None,
            data_status="UNAVAILABLE", signal_changed_today=False, error="boom",
        )

    monkeypatch.setattr(watchlist_service, "_enrich", failing_enrich)
    result = watchlist_service.get_watchlist("wl8")
    assert result.entries[0].error == "boom"
    assert result.entries[0].data_status == "UNAVAILABLE"
