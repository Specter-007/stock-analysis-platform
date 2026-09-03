"""Tests for fundamental data extraction and the optional fundamental /
overall score. Uses synthetic `.info`-shaped dicts - real yfinance payloads
are covered by the real-network integration suite.
"""
import pytest

from app.fundamentals.score import compute_fundamental_score, compute_overall_score
from app.fundamentals.service import extract_fundamentals

HEALTHY_INFO = {
    "trailingPE": 20.0,
    "forwardPE": 18.0,
    "trailingPegRatio": 1.5,
    "priceToSalesTrailing12Months": 5.0,
    "priceToBook": 4.0,
    "revenueGrowth": 0.15,
    "earningsGrowth": 0.20,
    "profitMargins": 0.25,
    "operatingMargins": 0.30,
    "returnOnEquity": 0.35,
    "debtToEquity": 50.0,
    "currentRatio": 1.5,
    "freeCashflow": 1_000_000.0,
}

UNHEALTHY_INFO = {
    "trailingPE": 200.0,
    "trailingPegRatio": 10.0,
    "priceToBook": 50.0,
    "revenueGrowth": -0.10,
    "earningsGrowth": -0.20,
    "profitMargins": 0.02,
    "operatingMargins": 0.01,
    "returnOnEquity": 0.02,
    "debtToEquity": 500.0,
    "currentRatio": 0.5,
}

EMPTY_INFO = {"trailingPegRatio": None}


def test_extract_fundamentals_maps_percentage_fields_correctly():
    result = extract_fundamentals(HEALTHY_INFO)
    revenue_growth = next(m for m in result.growth if m.key == "revenue_growth")
    assert revenue_growth.value == pytest.approx(15.0)
    assert revenue_growth.unit == "%"


def test_extract_fundamentals_debt_to_equity_not_double_scaled():
    result = extract_fundamentals(HEALTHY_INFO)
    dte = next(m for m in result.balance_sheet if m.key == "debt_to_equity")
    assert dte.value == pytest.approx(50.0)  # NOT 5000.0 - already a percentage from Yahoo


def test_extract_fundamentals_missing_fields_are_none():
    result = extract_fundamentals(EMPTY_INFO)
    assert result.has_any_data is False
    for metric in result.valuation + result.growth + result.profitability + result.balance_sheet:
        assert metric.value is None


def test_fundamental_score_higher_for_healthy_metrics():
    healthy = compute_fundamental_score(extract_fundamentals(HEALTHY_INFO))
    unhealthy = compute_fundamental_score(extract_fundamentals(UNHEALTHY_INFO))
    assert healthy.score is not None
    assert unhealthy.score is not None
    assert healthy.score > unhealthy.score


def test_fundamental_score_none_when_no_data_available():
    result = compute_fundamental_score(extract_fundamentals(EMPTY_INFO))
    assert result.score is None
    assert all(f.value is None for f in result.factors)


def test_fundamental_score_excludes_missing_metrics_from_normalization():
    partial_info = {"revenueGrowth": 0.20, "earningsGrowth": 0.20}
    result = compute_fundamental_score(extract_fundamentals(partial_info))
    # Both available metrics are healthy -> should score 100, not penalized
    # for the many metrics Yahoo didn't report.
    assert result.score == pytest.approx(100.0)


def test_overall_score_is_explicit_weighted_blend():
    overall = compute_overall_score(technical_score=80.0, fundamental_score=60.0, technical_weight=0.6, fundamental_weight=0.4)
    assert overall == pytest.approx(80.0 * 0.6 + 60.0 * 0.4)


def test_overall_score_none_when_fundamental_unavailable():
    overall = compute_overall_score(technical_score=80.0, fundamental_score=None, technical_weight=0.6, fundamental_weight=0.4)
    assert overall is None
