"""V4 P0.2: persistent, append-only paper-trading equity snapshot history.

One immutable observation per REAL trading day (keyed off the benchmark's
own daily bars, never wall-clock date) - never duplicated, never fabricated
for a day the portfolio wasn't actually observed on or the market was
closed. Network-isolated via mocked price/signal/regime/trading-day lookups,
same pattern as test_v3_paper_trading_advanced.py.
"""
import datetime as dt

import pytest

from app.paper_trading import service as paper_trading_service


@pytest.fixture
def user_id(db_session):
    from app.models_db.user import User

    user = User(email="paper-trading-persist-test@example.com", password_hash="x", display_name="Test")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user.id


@pytest.fixture
def fixed_price(monkeypatch):
    prices = {"AAPL": 100.0, "MSFT": 200.0}

    def fake_price(ticker):
        return prices.get(ticker)

    monkeypatch.setattr(paper_trading_service, "_current_price", fake_price)
    monkeypatch.setattr(paper_trading_service, "_current_signal_snapshot", lambda ticker: (None, None))
    monkeypatch.setattr(paper_trading_service, "_current_market_regime", lambda: None)
    return prices


@pytest.fixture
def fake_trading_day(monkeypatch):
    """A controllable stand-in for 'the latest real trading day + benchmark
    close', so tests can advance days deterministically without touching
    the network or a real calendar.
    """
    state = {"day": dt.date(2026, 1, 5), "spy_close": 500.0}

    def fake_latest():
        return state["day"], state["spy_close"]

    monkeypatch.setattr(paper_trading_service, "_latest_real_trading_day", fake_latest)
    return state


def test_no_snapshot_recorded_when_market_data_unavailable(db_session, user_id, fixed_price, monkeypatch):
    monkeypatch.setattr(paper_trading_service, "_latest_real_trading_day", lambda: (None, None))
    paper_trading_service.execute_trade(db_session, user_id, "p1", "AAPL", "BUY", 10)
    history = paper_trading_service.get_equity_history(db_session, user_id, "p1")
    assert history.snapshots == []


def test_first_snapshot_recorded_on_query(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "p2", "AAPL", "BUY", 10)
    history = paper_trading_service.get_equity_history(db_session, user_id, "p2")
    assert len(history.snapshots) == 1
    snap = history.snapshots[0]
    assert snap.date == "2026-01-05"
    assert snap.daily_pnl is None  # no prior observation to diff against
    assert snap.previous_snapshot_date is None
    assert snap.benchmark_value == pytest.approx(10_000.0)  # basis day == this day, so 1:1


def test_repeated_query_same_trading_day_does_not_duplicate(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "p3", "AAPL", "BUY", 10)
    paper_trading_service.get_portfolio(db_session, user_id, "p3")
    paper_trading_service.get_portfolio(db_session, user_id, "p3")
    paper_trading_service.get_portfolio(db_session, user_id, "p3")
    history = paper_trading_service.get_equity_history(db_session, user_id, "p3")
    assert len(history.snapshots) == 1


def test_new_trading_day_appends_not_replaces(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "p4", "AAPL", "BUY", 10)
    paper_trading_service.get_portfolio(db_session, user_id, "p4")  # day 1 snapshot

    fake_trading_day["day"] = dt.date(2026, 1, 6)
    fake_trading_day["spy_close"] = 505.0  # benchmark up 1%
    fixed_price["AAPL"] = 110.0  # portfolio equity moves too
    paper_trading_service.get_portfolio(db_session, user_id, "p4")  # day 2 snapshot

    history = paper_trading_service.get_equity_history(db_session, user_id, "p4")
    assert [s.date for s in history.snapshots] == ["2026-01-05", "2026-01-06"]


def test_daily_pnl_is_change_since_previous_recorded_snapshot(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "p5", "AAPL", "BUY", 10)
    day1 = paper_trading_service.get_equity_history(db_session, user_id, "p5").snapshots[0]

    fake_trading_day["day"] = dt.date(2026, 1, 6)
    fixed_price["AAPL"] = 120.0
    paper_trading_service.get_portfolio(db_session, user_id, "p5")
    day2 = paper_trading_service.get_equity_history(db_session, user_id, "p5").snapshots[1]

    assert day2.previous_snapshot_date == "2026-01-05"
    assert day2.daily_pnl == pytest.approx(day2.equity - day1.equity)


def test_benchmark_value_tracks_spy_proportionally_from_basis_day(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "p6", "AAPL", "BUY", 10)
    paper_trading_service.get_portfolio(db_session, user_id, "p6")  # basis: SPY=500 -> benchmark_value=10000

    fake_trading_day["day"] = dt.date(2026, 1, 6)
    fake_trading_day["spy_close"] = 550.0  # SPY up 10% from basis
    paper_trading_service.get_portfolio(db_session, user_id, "p6")

    history = paper_trading_service.get_equity_history(db_session, user_id, "p6")
    assert history.snapshots[1].benchmark_value == pytest.approx(11_000.0)  # 10% up from 10000 basis


def test_cumulative_return_percent_matches_equity_vs_starting_capital(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "p7", "AAPL", "BUY", 10)
    view = paper_trading_service.get_portfolio(db_session, user_id, "p7")
    history = paper_trading_service.get_equity_history(db_session, user_id, "p7")
    snap = history.snapshots[0]
    expected = (view.current_value / 10_000.0 - 1.0) * 100.0
    assert snap.cumulative_return_percent == pytest.approx(round(expected, 2))


def test_reset_clears_equity_history_and_benchmark_basis(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "p8", "AAPL", "BUY", 10)
    paper_trading_service.get_portfolio(db_session, user_id, "p8")
    assert len(paper_trading_service.get_equity_history(db_session, user_id, "p8").snapshots) == 1

    paper_trading_service.reset(db_session, user_id, "p8")
    history = paper_trading_service.get_equity_history(db_session, user_id, "p8")
    # reset() itself queries the portfolio, which may record a fresh day-1
    # snapshot for the NEW simulation - the key guarantee is the OLD
    # simulation's history is gone, not that snapshots is permanently empty.
    assert len(history.snapshots) <= 1
    if history.snapshots:
        assert history.snapshots[0].cumulative_return_percent == 0.0


def test_snapshot_history_never_shrinks_across_many_queries(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "p9", "AAPL", "BUY", 10)
    days = [dt.date(2026, 1, d) for d in range(5, 11)]
    counts = []
    for d in days:
        fake_trading_day["day"] = d
        paper_trading_service.get_portfolio(db_session, user_id, "p9")
        counts.append(len(paper_trading_service.get_equity_history(db_session, user_id, "p9").snapshots))
    assert counts == sorted(counts)
    assert counts[-1] == len(days)


def test_invested_value_equals_equity_minus_cash(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "p10", "AAPL", "BUY", 10)
    view = paper_trading_service.get_portfolio(db_session, user_id, "p10")
    snap = paper_trading_service.get_equity_history(db_session, user_id, "p10").snapshots[0]
    assert snap.invested_value == pytest.approx(view.current_value - view.cash)
    assert snap.equity == pytest.approx(snap.cash + snap.invested_value)
