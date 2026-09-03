"""Tests for paper-trading position sizing rules. Long-only, no leverage:
every mode must be incapable of producing a share count whose cost exceeds
available cash or the configured max-position-percent backstop.
"""
import pytest

from app.paper_trading.sizing import PositionSizingError, SizingRequest, calculate_shares


def test_fixed_shares_returns_requested_amount_when_affordable():
    req = SizingRequest(mode="FIXED_SHARES", price=100.0, portfolio_equity=10_000, available_cash=10_000, shares=10)
    assert calculate_shares(req) == pytest.approx(10.0)


def test_fixed_shares_capped_by_available_cash():
    req = SizingRequest(mode="FIXED_SHARES", price=100.0, portfolio_equity=10_000, available_cash=500, shares=10)
    shares = calculate_shares(req)
    assert shares * 100.0 <= 500.0 + 1e-6


def test_fixed_shares_requires_positive_shares():
    with pytest.raises(PositionSizingError):
        calculate_shares(SizingRequest(mode="FIXED_SHARES", price=100.0, portfolio_equity=10_000, available_cash=10_000, shares=0))


def test_fixed_capital_percent_allocates_correct_fraction():
    req = SizingRequest(
        mode="FIXED_CAPITAL_PERCENT", price=50.0, portfolio_equity=10_000, available_cash=10_000, capital_percent=10.0
    )
    shares = calculate_shares(req)
    assert shares * 50.0 == pytest.approx(1_000.0)


def test_fixed_capital_percent_respects_max_position_cap():
    req = SizingRequest(
        mode="FIXED_CAPITAL_PERCENT", price=50.0, portfolio_equity=10_000, available_cash=10_000,
        capital_percent=50.0, max_position_percent=20.0,
    )
    shares = calculate_shares(req)
    assert shares * 50.0 <= 10_000 * 0.20 + 1e-6


def test_risk_percent_sizes_so_stop_loss_hit_matches_risk_budget():
    req = SizingRequest(
        mode="RISK_PERCENT", price=100.0, portfolio_equity=10_000, available_cash=10_000,
        risk_percent=1.0, stop_loss_percent=5.0,
    )
    shares = calculate_shares(req)
    loss_if_stopped = shares * (100.0 * 0.05)
    assert loss_if_stopped == pytest.approx(10_000 * 0.01, rel=1e-6)


def test_risk_percent_requires_stop_loss_percent():
    with pytest.raises(PositionSizingError):
        calculate_shares(
            SizingRequest(mode="RISK_PERCENT", price=100.0, portfolio_equity=10_000, available_cash=10_000, risk_percent=1.0)
        )


def test_risk_percent_capped_by_available_cash():
    req = SizingRequest(
        mode="RISK_PERCENT", price=10.0, portfolio_equity=1_000_000, available_cash=100,
        risk_percent=50.0, stop_loss_percent=1.0,
    )
    shares = calculate_shares(req)
    assert shares * 10.0 <= 100.0 + 1e-6


def test_unknown_mode_rejected():
    with pytest.raises(PositionSizingError):
        calculate_shares(SizingRequest(mode="LEVERAGE_10X", price=100.0, portfolio_equity=10_000, available_cash=10_000))


def test_zero_price_rejected():
    with pytest.raises(PositionSizingError):
        calculate_shares(SizingRequest(mode="FIXED_SHARES", price=0.0, portfolio_equity=10_000, available_cash=10_000, shares=10))


def test_no_mode_ever_returns_shares_costing_more_than_equity():
    """A generic property check across all three modes with generous inputs -
    the max-position-percent backstop must always hold."""
    common = dict(price=25.0, portfolio_equity=10_000, available_cash=10_000, max_position_percent=20.0)
    for req in (
        SizingRequest(mode="FIXED_SHARES", shares=100_000, **common),
        SizingRequest(mode="FIXED_CAPITAL_PERCENT", capital_percent=100.0, **common),
        SizingRequest(mode="RISK_PERCENT", risk_percent=100.0, stop_loss_percent=1.0, **common),
    ):
        shares = calculate_shares(req)
        assert shares * 25.0 <= 10_000 * 0.20 + 1e-6
