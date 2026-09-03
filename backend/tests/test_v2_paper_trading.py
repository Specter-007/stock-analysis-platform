"""Paper-trading portfolio tests. SIMULATION ONLY feature - these tests
isolate the JSON store to a temp directory and mock live-quote/signal/regime
lookups so they're deterministic, fast, and don't touch the network.

Since V3 added realistic commission + slippage (see `app.config
.PAPER_TRADING_COMMISSION_BPS/SLIPPAGE_BPS`, 5 bps each => 10 bps combined
round-trip-per-leg), every fill price differs from the raw quote by a factor
of (1 +/- 0.001). Expected values below are computed from that cost model,
not the raw quote - see `tests/test_v3_paper_trading_costs.py` for tests
that isolate the cost math itself.
"""
import pytest

from app.paper_trading import service as paper_trading_service
from app.paper_trading import store as paper_trading_store

COST_RATE = 0.001  # (5 + 5) bps


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(paper_trading_store, "_DATA_DIR", tmp_path / "paper_trading")


@pytest.fixture
def fixed_price(monkeypatch):
    prices = {"AAPL": 100.0, "MSFT": 200.0}

    def fake_price(ticker):
        return prices.get(ticker)

    monkeypatch.setattr(paper_trading_service, "_current_price", fake_price)
    # Isolate from the network: the journal's entry/exit signal snapshot and
    # market-regime lookups are best-effort extras, not part of what these
    # accounting tests are checking.
    monkeypatch.setattr(paper_trading_service, "_current_signal_snapshot", lambda ticker: (None, None))
    monkeypatch.setattr(paper_trading_service, "_current_market_regime", lambda: None)
    return prices


def test_new_portfolio_starts_with_default_capital(fixed_price):
    view = paper_trading_service.get_portfolio("test1")
    assert view.cash == 10_000.0
    assert view.starting_capital == 10_000.0
    assert view.positions == []
    assert view.current_value == 10_000.0


def test_buy_reduces_cash_and_creates_position(fixed_price):
    view = paper_trading_service.execute_trade("test2", "AAPL", "BUY", 10)
    fill_price = 100.0 * (1 + COST_RATE)
    assert view.cash == pytest.approx(10_000.0 - 10 * fill_price)
    assert len(view.positions) == 1
    assert view.positions[0].shares == 10
    assert view.positions[0].avg_entry_price == pytest.approx(fill_price)


def test_buy_insufficient_funds_rejected(fixed_price):
    with pytest.raises(paper_trading_service.PaperTradingError):
        paper_trading_service.execute_trade("test3", "AAPL", "BUY", 1_000_000)


def test_sell_more_than_held_rejected(fixed_price):
    paper_trading_service.execute_trade("test4", "AAPL", "BUY", 5)
    with pytest.raises(paper_trading_service.PaperTradingError):
        paper_trading_service.execute_trade("test4", "AAPL", "SELL", 10)


def test_sell_computes_realized_pnl(fixed_price):
    paper_trading_service.execute_trade("test5", "AAPL", "BUY", 10)
    fixed_price["AAPL"] = 150.0  # price rises after entry
    view = paper_trading_service.execute_trade("test5", "AAPL", "SELL", 10)
    # gross = (150-100)*10 = 500; fees+slippage = 10*(100+150)*0.001 = 2.5; net = 497.5
    assert view.realized_pnl == pytest.approx(497.5)
    assert view.positions == []
    trade = view.trades[-1]
    assert trade.gross_pnl == pytest.approx(500.0)
    assert trade.net_pnl == pytest.approx(497.5)
    assert trade.fees is not None and trade.slippage is not None
    assert trade.exit_reason == "MANUAL_PAPER_EXIT"


def test_partial_sell_keeps_remaining_position_and_entry_price(fixed_price):
    paper_trading_service.execute_trade("test6", "AAPL", "BUY", 10)
    view = paper_trading_service.execute_trade("test6", "AAPL", "SELL", 4)
    assert len(view.positions) == 1
    assert view.positions[0].shares == pytest.approx(6.0)
    assert view.positions[0].avg_entry_price == pytest.approx(100.0 * (1 + COST_RATE))


def test_average_entry_price_updates_on_additional_buys(fixed_price):
    paper_trading_service.execute_trade("test7", "AAPL", "BUY", 10)  # @100 -> fill 100.1
    fixed_price["AAPL"] = 200.0
    view = paper_trading_service.execute_trade("test7", "AAPL", "BUY", 10)  # @200 -> fill 200.2
    assert view.positions[0].shares == pytest.approx(20.0)
    expected_avg = (10 * 100.0 * (1 + COST_RATE) + 10 * 200.0 * (1 + COST_RATE)) / 20
    assert view.positions[0].avg_entry_price == pytest.approx(expected_avg)


def test_unrealized_pnl_reflects_live_price_changes(fixed_price):
    paper_trading_service.execute_trade("test8", "AAPL", "BUY", 10)  # cost basis ~1001
    fixed_price["AAPL"] = 120.0
    view = paper_trading_service.get_portfolio("test8")
    cost_basis = 10 * 100.0 * (1 + COST_RATE)
    expected_unrealized = 10 * 120.0 - cost_basis
    assert view.positions[0].unrealized_pnl == pytest.approx(expected_unrealized)
    assert view.unrealized_pnl == pytest.approx(expected_unrealized)


def test_reset_restores_default_state(fixed_price):
    paper_trading_service.execute_trade("test9", "AAPL", "BUY", 10)
    view = paper_trading_service.reset("test9", starting_capital=5_000.0)
    assert view.cash == 5_000.0
    assert view.starting_capital == 5_000.0
    assert view.positions == []
    assert view.trades == []


def test_invalid_action_rejected(fixed_price):
    with pytest.raises(paper_trading_service.PaperTradingError):
        paper_trading_service.execute_trade("test10", "AAPL", "HOLD", 1)


def test_zero_or_negative_shares_rejected(fixed_price):
    with pytest.raises(paper_trading_service.PaperTradingError):
        paper_trading_service.execute_trade("test11", "AAPL", "BUY", 0)


def test_trades_are_persisted_across_portfolio_loads(fixed_price):
    paper_trading_service.execute_trade("test12", "AAPL", "BUY", 5)
    paper_trading_service.execute_trade("test12", "MSFT", "BUY", 2)
    view = paper_trading_service.get_portfolio("test12")
    assert len(view.trades) == 2
    assert {p.ticker for p in view.positions} == {"AAPL", "MSFT"}


def test_portfolios_are_isolated_by_id(fixed_price):
    paper_trading_service.execute_trade("alice", "AAPL", "BUY", 10)
    bob_view = paper_trading_service.get_portfolio("bob")
    assert bob_view.cash == 10_000.0
    assert bob_view.positions == []
