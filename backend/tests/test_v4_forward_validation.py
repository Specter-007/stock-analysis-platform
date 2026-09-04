"""V4 P0.3: Forward Validation engine - a distinct concept from historical
backtesting/out-of-sample validation. Built entirely on top of the existing
paper-trading service and its append-only equity snapshots; never
re-implements portfolio math or fabricates observations.
"""
import datetime as dt

import pytest

from app.paper_trading import forward_validation
from app.paper_trading import service as paper_trading_service


@pytest.fixture
def user_id(db_session):
    from app.models_db.user import User

    user = User(email="forward-validation-test@example.com", password_hash="x", display_name="Test")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user.id


@pytest.fixture
def fixed_price(monkeypatch):
    prices = {"AAPL": 100.0}

    def fake_price(ticker):
        return prices.get(ticker)

    monkeypatch.setattr(paper_trading_service, "_current_price", fake_price)
    monkeypatch.setattr(paper_trading_service, "_current_signal_snapshot", lambda ticker: (None, None))
    monkeypatch.setattr(paper_trading_service, "_current_market_regime", lambda: None)
    return prices


@pytest.fixture
def fake_trading_day(monkeypatch):
    state = {"day": dt.date(2026, 1, 5), "spy_close": 500.0}

    def fake_latest():
        return state["day"], state["spy_close"]

    monkeypatch.setattr(paper_trading_service, "_latest_real_trading_day", fake_latest)
    return state


def test_no_observations_yet_reports_none_dates_and_no_crash(db_session, user_id, fixed_price, monkeypatch):
    monkeypatch.setattr(paper_trading_service, "_latest_real_trading_day", lambda: (None, None))
    view = forward_validation.get_forward_validation(db_session, user_id, "fv_empty")
    assert view.start_date is None
    assert view.current_date is None
    assert view.trading_days_observed == 0
    assert view.insufficient_sample is True


def test_single_day_is_flagged_insufficient_sample(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "fv1", "AAPL", "BUY", 10)
    view = forward_validation.get_forward_validation(db_session, user_id, "fv1")
    assert view.trading_days_observed == 1
    assert view.insufficient_sample is True
    assert any("trading day" in w for w in view.warnings)


def test_start_and_current_date_match_first_and_last_snapshot(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "fv2", "AAPL", "BUY", 10)
    for d in range(6, 12):
        fake_trading_day["day"] = dt.date(2026, 1, d)
        paper_trading_service.get_portfolio(db_session, user_id, "fv2")

    view = forward_validation.get_forward_validation(db_session, user_id, "fv2")
    assert view.start_date == "2026-01-05"
    assert view.current_date == "2026-01-11"
    assert view.trading_days_observed == 7


def test_sample_no_longer_insufficient_past_threshold(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "fv3", "AAPL", "BUY", 10)
    for i in range(1, 25):
        fake_trading_day["day"] = dt.date(2026, 1, 1) + dt.timedelta(days=i)
        paper_trading_service.get_portfolio(db_session, user_id, "fv3")

    view = forward_validation.get_forward_validation(db_session, user_id, "fv3")
    assert view.trading_days_observed >= forward_validation.MIN_TRADING_DAYS_FOR_CONFIDENT_METRICS
    assert view.insufficient_sample is False


def test_benchmark_return_percent_matches_snapshot_curve(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "fv4", "AAPL", "BUY", 10)  # basis: SPY=500

    fake_trading_day["day"] = dt.date(2026, 1, 6)
    fake_trading_day["spy_close"] = 525.0  # +5%
    paper_trading_service.get_portfolio(db_session, user_id, "fv4")

    view = forward_validation.get_forward_validation(db_session, user_id, "fv4")
    assert view.benchmark_return_percent == pytest.approx(5.0, abs=0.01)


def test_max_drawdown_computed_from_recorded_equity_curve(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "fv5", "AAPL", "BUY", 10)  # day1: equity ~10000

    fake_trading_day["day"] = dt.date(2026, 1, 6)
    fixed_price["AAPL"] = 150.0  # equity rallies
    paper_trading_service.get_portfolio(db_session, user_id, "fv5")

    fake_trading_day["day"] = dt.date(2026, 1, 7)
    fixed_price["AAPL"] = 90.0  # equity pulls back well below the peak
    paper_trading_service.get_portfolio(db_session, user_id, "fv5")

    view = forward_validation.get_forward_validation(db_session, user_id, "fv5")
    assert view.max_drawdown_percent is not None
    assert view.max_drawdown_percent < 0


def test_max_drawdown_none_with_fewer_than_two_observations(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "fv6", "AAPL", "BUY", 10)
    view = forward_validation.get_forward_validation(db_session, user_id, "fv6")
    assert view.max_drawdown_percent is None


def test_model_version_reported_for_new_portfolio_matches_current(db_session, user_id, fixed_price, fake_trading_day):
    from app.config import MODEL_VERSION_CURRENT

    paper_trading_service.execute_trade(db_session, user_id, "fv7", "AAPL", "BUY", 10)
    view = forward_validation.get_forward_validation(db_session, user_id, "fv7")
    assert view.model_version == MODEL_VERSION_CURRENT
    assert view.model_version_is_mixed is False


def test_realized_and_unrealized_pnl_match_portfolio_view(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "fv8", "AAPL", "BUY", 10)
    fixed_price["AAPL"] = 120.0
    portfolio_view = paper_trading_service.get_portfolio(db_session, user_id, "fv8")

    view = forward_validation.get_forward_validation(db_session, user_id, "fv8")
    assert view.realized_pnl == portfolio_view.realized_pnl
    assert view.unrealized_pnl == portfolio_view.unrealized_pnl
    assert view.open_positions_count == portfolio_view.number_of_positions


def test_number_of_trades_counts_buy_and_sell_events(db_session, user_id, fixed_price, fake_trading_day):
    paper_trading_service.execute_trade(db_session, user_id, "fv9", "AAPL", "BUY", 10)
    paper_trading_service.execute_trade(db_session, user_id, "fv9", "AAPL", "SELL", 5)
    view = forward_validation.get_forward_validation(db_session, user_id, "fv9")
    assert view.number_of_trades == 2
