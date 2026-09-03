"""V4 P2.7: model-vs-model (v1.0 vs v1.1) forward comparison."""
import pytest

from app.model_evaluation.comparison import compare_model_versions


def test_backtest_comparison_covers_every_supported_version(ohlcv_long):
    from app.config import SUPPORTED_MODEL_VERSIONS

    result = compare_model_versions(
        ticker="TEST", full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(), end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    versions = {r["model_version"] for r in result["backtest_comparison"]}
    assert versions == set(SUPPORTED_MODEL_VERSIONS)


def test_forward_comparison_empty_when_no_portfolios_supplied(ohlcv_long):
    result = compare_model_versions(
        ticker="TEST", full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(), end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    assert result["forward_comparison"] == []


def test_forward_comparison_populated_when_portfolios_supplied(monkeypatch, ohlcv_long):
    from app.model_evaluation import comparison as comparison_module

    class FakeForwardView:
        def __init__(self, days):
            self.trading_days_observed = days
            self.total_return_percent = 2.5
            self.insufficient_sample = days < 20

    def fake_get_forward_validation(portfolio_id):
        return FakeForwardView(5 if portfolio_id == "p_v1" else 30)

    monkeypatch.setattr(comparison_module.forward_validation, "get_forward_validation", fake_get_forward_validation)

    result = compare_model_versions(
        ticker="TEST", full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(), end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
        forward_portfolio_ids={"1.0": "p_v1", "1.1": "p_v2"},
    )
    forward_by_version = {r["model_version"]: r for r in result["forward_comparison"]}
    assert forward_by_version["1.0"]["insufficient_sample"] is True
    assert forward_by_version["1.1"]["insufficient_sample"] is False


def test_methodology_disclaims_statistical_superiority_claims(ohlcv_long):
    result = compare_model_versions(
        ticker="TEST", full_price_df=ohlcv_long,
        start_date=ohlcv_long.index[220].date(), end_date=ohlcv_long.index[-1].date(),
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    assert "NOT a claim" in result["methodology"]
