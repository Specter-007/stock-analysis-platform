"""Tests for the V3 advanced paper-trading features: stop-loss/take-profit/
trailing-stop auto-exits, position-sizing integration, cost breakdown, and
the portfolio risk dashboard. Network-isolated via mocked price/signal/
regime lookups, same pattern as test_v2_paper_trading.py.
"""
import pytest

from app.paper_trading import risk as paper_risk
from app.paper_trading import service as paper_trading_service


@pytest.fixture
def user_id(db_session):
    from app.models_db.user import User

    user = User(email="paper-trading-adv-test@example.com", password_hash="x", display_name="Test")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user.id


@pytest.fixture
def fixed_price(monkeypatch):
    prices = {"AAPL": 100.0, "MSFT": 200.0, "TSLA": 50.0, "JNJ": 150.0, "XOM": 100.0}

    def fake_price(ticker):
        return prices.get(ticker)

    monkeypatch.setattr(paper_trading_service, "_current_price", fake_price)
    monkeypatch.setattr(paper_trading_service, "_current_signal_snapshot", lambda ticker: (None, None))
    monkeypatch.setattr(paper_trading_service, "_current_market_regime", lambda: None)
    return prices


@pytest.fixture
def mocked_sector(monkeypatch):
    def fake_overview(ticker):
        sectors = {
            "AAPL": "Technology", "MSFT": "Technology", "TSLA": "Consumer Cyclical",
            "JNJ": "Healthcare", "XOM": "Energy",
        }
        return {"sector": sectors.get(ticker, "Unknown")}, None

    monkeypatch.setattr(paper_risk.market_data, "get_overview", fake_overview)


# --------------------------------------------------------------- Stop-loss

def test_stop_loss_triggers_automatic_exit(db_session, user_id, fixed_price):
    paper_trading_service.execute_trade(db_session, user_id, "sl1", "AAPL", "BUY", 10, stop_loss_percent=5.0)
    fixed_price["AAPL"] = 94.0  # more than 5% below entry of 100
    view = paper_trading_service.get_portfolio(db_session, user_id, "sl1")
    assert view.positions == []
    exit_trade = next(t for t in view.trades if t.action == "SELL")
    assert exit_trade.exit_reason == "STOP_LOSS"


def test_stop_loss_does_not_trigger_above_threshold(db_session, user_id, fixed_price):
    paper_trading_service.execute_trade(db_session, user_id, "sl2", "AAPL", "BUY", 10, stop_loss_percent=5.0)
    fixed_price["AAPL"] = 96.0  # only 4% below entry
    view = paper_trading_service.get_portfolio(db_session, user_id, "sl2")
    assert len(view.positions) == 1


def test_take_profit_triggers_automatic_exit(db_session, user_id, fixed_price):
    paper_trading_service.execute_trade(db_session, user_id, "tp1", "AAPL", "BUY", 10, take_profit_percent=10.0)
    fixed_price["AAPL"] = 112.0  # more than 10% above entry
    view = paper_trading_service.get_portfolio(db_session, user_id, "tp1")
    assert view.positions == []
    exit_trade = next(t for t in view.trades if t.action == "SELL")
    assert exit_trade.exit_reason == "TAKE_PROFIT"


def test_trailing_stop_triggers_after_price_pulls_back_from_peak(db_session, user_id, fixed_price):
    paper_trading_service.execute_trade(db_session, user_id, "ts1", "AAPL", "BUY", 10, trailing_stop_percent=5.0)
    fixed_price["AAPL"] = 130.0  # price rallies - raises the trailing peak
    paper_trading_service.get_portfolio(db_session, user_id, "ts1")  # triggers peak update
    fixed_price["AAPL"] = 122.0  # pulls back >5% from the 130 peak (not from entry)
    view = paper_trading_service.get_portfolio(db_session, user_id, "ts1")
    assert view.positions == []
    exit_trade = next(t for t in view.trades if t.action == "SELL")
    assert exit_trade.exit_reason == "TRAILING_STOP"


def test_trailing_stop_does_not_trigger_on_pullback_from_entry_if_still_above_peak_threshold(db_session, user_id, fixed_price):
    paper_trading_service.execute_trade(db_session, user_id, "ts2", "AAPL", "BUY", 10, trailing_stop_percent=20.0)
    fixed_price["AAPL"] = 130.0
    paper_trading_service.get_portfolio(db_session, user_id, "ts2")
    fixed_price["AAPL"] = 110.0  # down from peak of 130 by ~15% - inside the 20% trailing band
    view = paper_trading_service.get_portfolio(db_session, user_id, "ts2")
    assert len(view.positions) == 1


def test_no_exit_controls_means_no_auto_exit_regardless_of_price_move(db_session, user_id, fixed_price):
    paper_trading_service.execute_trade(db_session, user_id, "ne1", "AAPL", "BUY", 10)
    fixed_price["AAPL"] = 1.0  # huge drop, but no stop-loss was set
    view = paper_trading_service.get_portfolio(db_session, user_id, "ne1")
    assert len(view.positions) == 1


def test_manual_sell_reason_is_manual_paper_exit(db_session, user_id, fixed_price):
    paper_trading_service.execute_trade(db_session, user_id, "m1", "AAPL", "BUY", 10)
    view = paper_trading_service.execute_trade(db_session, user_id, "m1", "AAPL", "SELL", 10)
    assert view.trades[-1].exit_reason == "MANUAL_PAPER_EXIT"


def test_close_all_positions_uses_end_of_test_reason(db_session, user_id, fixed_price):
    paper_trading_service.execute_trade(db_session, user_id, "ca1", "AAPL", "BUY", 5)
    paper_trading_service.execute_trade(db_session, user_id, "ca1", "MSFT", "BUY", 2)
    view = paper_trading_service.close_all_positions(db_session, user_id, "ca1")
    assert view.positions == []
    sells = [t for t in view.trades if t.action == "SELL"]
    assert len(sells) == 2
    assert all(t.exit_reason == "END_OF_TEST" for t in sells)


# ----------------------------------------------------------- Cost breakdown

def test_trade_journal_reports_gross_fees_slippage_net_separately(db_session, user_id, fixed_price):
    paper_trading_service.execute_trade(db_session, user_id, "cost1", "AAPL", "BUY", 10)
    fixed_price["AAPL"] = 110.0
    view = paper_trading_service.execute_trade(db_session, user_id, "cost1", "AAPL", "SELL", 10)
    sell_trade = view.trades[-1]
    assert sell_trade.gross_pnl is not None
    assert sell_trade.fees is not None and sell_trade.fees > 0
    assert sell_trade.slippage is not None and sell_trade.slippage > 0
    assert sell_trade.net_pnl == pytest.approx(sell_trade.gross_pnl - sell_trade.fees - sell_trade.slippage)


# ------------------------------------------------------------ Position sizing

def test_fixed_capital_percent_sizing_via_execute_trade(db_session, user_id, fixed_price):
    view = paper_trading_service.execute_trade(db_session, user_id, "size1", "AAPL", "BUY", shares=None, sizing_mode="FIXED_CAPITAL_PERCENT", capital_percent=10.0
    )
    # 10% of 10,000 = 1,000 notional at raw price 100 (before cost haircut) ~= 10 shares
    assert view.positions[0].shares == pytest.approx(10.0, rel=0.01)


def test_risk_percent_sizing_via_execute_trade(db_session, user_id, fixed_price):
    view = paper_trading_service.execute_trade(db_session, user_id, "size2", "AAPL", "BUY", shares=None, sizing_mode="RISK_PERCENT",
        risk_percent=1.0, stop_loss_percent=5.0,
    )
    # risking 1% of 10,000 = 100, stop distance = 100*0.05 = 5/share -> ~20 shares
    assert view.positions[0].shares == pytest.approx(20.0, rel=0.01)
    assert view.positions[0].stop_loss_percent == pytest.approx(5.0)


def test_sizing_without_shares_or_mode_defaults_to_fixed_shares_and_fails_without_shares(db_session, user_id, fixed_price):
    with pytest.raises(paper_trading_service.PaperTradingError):
        paper_trading_service.execute_trade(db_session, user_id, "size3", "AAPL", "BUY", shares=None)


# ------------------------------------------------------------ Risk dashboard

def test_risk_dashboard_flags_high_concentration(db_session, user_id, fixed_price, mocked_sector):
    paper_trading_service.execute_trade(db_session, user_id, "risk1", "AAPL", "BUY", 50)  # ~$5,005 of $10,000 portfolio
    view = paper_trading_service.get_portfolio(db_session, user_id, "risk1")
    result = paper_risk.assess_portfolio_risk(view)
    assert any("HIGH_CONCENTRATION" in w for w in result.warnings)


def test_risk_dashboard_no_warnings_for_diversified_small_positions(db_session, user_id, fixed_price, mocked_sector):
    # Spread across three DIFFERENT sectors so no single one can dominate
    # invested capital merely from having too few sectors to divide among
    # (with only 2 sectors, one is mathematically guaranteed >= 50%).
    paper_trading_service.execute_trade(db_session, user_id, "risk2", "AAPL", "BUY", 3)  # Technology, ~$300
    paper_trading_service.execute_trade(db_session, user_id, "risk2", "TSLA", "BUY", 6)  # Consumer Cyclical, ~$300
    paper_trading_service.execute_trade(db_session, user_id, "risk2", "JNJ", "BUY", 2)  # Healthcare, ~$300
    view = paper_trading_service.get_portfolio(db_session, user_id, "risk2")
    result = paper_risk.assess_portfolio_risk(view)
    assert not any("HIGH_CONCENTRATION" in w for w in result.warnings)


def test_risk_dashboard_sector_concentration_sums_to_100(db_session, user_id, fixed_price, mocked_sector):
    paper_trading_service.execute_trade(db_session, user_id, "risk3", "AAPL", "BUY", 5)
    paper_trading_service.execute_trade(db_session, user_id, "risk3", "TSLA", "BUY", 5)
    view = paper_trading_service.get_portfolio(db_session, user_id, "risk3")
    result = paper_risk.assess_portfolio_risk(view)
    assert sum(result.sector_concentration.values()) == pytest.approx(100.0, abs=0.5)


def test_risk_dashboard_low_cash_warning(db_session, user_id, fixed_price, mocked_sector):
    # max_position_percent must be raised above its default (20%) backstop
    # for a 98% capital_percent request to actually be honored - the
    # backstop applying instead is separately covered in test_v3_position_sizing.py.
    paper_trading_service.execute_trade(db_session, user_id, "risk4", "AAPL", "BUY", shares=None, sizing_mode="FIXED_CAPITAL_PERCENT",
        capital_percent=98.0, max_position_percent=100.0,
    )
    view = paper_trading_service.get_portfolio(db_session, user_id, "risk4")
    result = paper_risk.assess_portfolio_risk(view)
    assert any("LOW_CASH" in w for w in result.warnings)


def test_risk_dashboard_no_warnings_for_all_cash_portfolio(db_session, user_id, fixed_price, mocked_sector):
    view = paper_trading_service.get_portfolio(db_session, user_id, "risk5")
    result = paper_risk.assess_portfolio_risk(view)
    assert result.warnings == []
    assert result.cash_percent == pytest.approx(100.0)
