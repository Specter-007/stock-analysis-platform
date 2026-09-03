"""V4 P1.5: multi-ticker stock comparison.

Network-isolated via mocked market_data calls, following the same pattern
used throughout the test suite (e.g. test_v3_paper_trading_advanced's
mocked_sector fixture).
"""
import pytest

from app.comparison.service import MAX_TICKERS, MIN_TICKERS, compare_stocks


@pytest.fixture
def mocked_market_data(monkeypatch, ohlcv_long):
    from app.comparison import service as comparison_module

    overviews = {
        "AAA": {"company_name": "Alpha Corp", "sector": "Technology", "industry": "Software",
                "last_price": 150.0, "change_percent": 1.2, "market_cap": 2_000_000_000.0},
        "BBB": {"company_name": "Beta Inc", "sector": "Healthcare", "industry": "Biotech",
                "last_price": 80.0, "change_percent": -0.5, "market_cap": 500_000_000.0},
    }
    infos = {
        "AAA": {"trailingPE": 25.0, "forwardPE": 20.0, "priceToBook": 5.0,
                "revenueGrowth": 0.15, "profitMargins": 0.22, "returnOnEquity": 0.18},
        "BBB": {},  # no fundamentals reported at all
    }

    def fake_get_overview(ticker):
        if ticker not in overviews:
            raise comparison_module.market_data.TickerNotFoundError(ticker)
        return overviews[ticker], None

    def fake_get_full_daily_history(ticker):
        return ohlcv_long, None

    def fake_fetch_info_raw(ticker):
        return infos.get(ticker, {})

    monkeypatch.setattr(comparison_module.market_data, "get_overview", fake_get_overview)
    monkeypatch.setattr(comparison_module.market_data, "get_full_daily_history", fake_get_full_daily_history)
    monkeypatch.setattr(comparison_module.market_data, "fetch_info_raw", fake_fetch_info_raw)
    return overviews


def test_compare_returns_one_row_per_ticker(mocked_market_data):
    result = compare_stocks(["AAA", "BBB"])
    assert len(result.rows) == 2
    assert {r.ticker for r in result.rows} == {"AAA", "BBB"}


def test_row_populates_market_data_fields(mocked_market_data):
    result = compare_stocks(["AAA", "BBB"])
    aaa = next(r for r in result.rows if r.ticker == "AAA")
    assert aaa.company_name == "Alpha Corp"
    assert aaa.sector == "Technology"
    assert aaa.last_price == 150.0
    assert aaa.error is None


def test_historical_volatility_is_not_double_scaled(mocked_market_data):
    """HIST_VOL_20 is already computed as a percentage (see
    app.indicators.volatility.historical_volatility) - a real stock's
    annualized historical volatility should read like ~10-100%, never
    the ~1800%+ that multiplying an already-percentage value by 100 again
    would produce.
    """
    result = compare_stocks(["AAA", "BBB"])
    for row in result.rows:
        if row.historical_volatility_percent is not None:
            assert 0 <= row.historical_volatility_percent < 500


def test_row_populates_technical_and_model_fields(mocked_market_data):
    result = compare_stocks(["AAA", "BBB"])
    aaa = next(r for r in result.rows if r.ticker == "AAA")
    assert aaa.trend_classification is not None
    assert aaa.signal in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
    assert aaa.score is not None
    assert aaa.model_version is not None


def test_missing_fundamentals_reported_as_none_not_zero(mocked_market_data):
    result = compare_stocks(["AAA", "BBB"])
    bbb = next(r for r in result.rows if r.ticker == "BBB")
    assert bbb.trailing_pe is None
    assert bbb.profit_margin_percent is None
    # explicitly NOT zero - missing must never look like a real 0% value
    assert bbb.trailing_pe != 0
    assert bbb.error is None  # BBB has an overview, just no fundamentals


def test_present_fundamentals_populated_correctly(mocked_market_data):
    result = compare_stocks(["AAA", "BBB"])
    aaa = next(r for r in result.rows if r.ticker == "AAA")
    assert aaa.trailing_pe == 25.0
    assert aaa.profit_margin_percent == pytest.approx(22.0)  # extract_fundamentals converts fraction -> percent


def test_ticker_not_found_reports_error_without_crashing_whole_comparison(mocked_market_data):
    result = compare_stocks(["AAA", "ZZZNOPE"])
    zzz = next(r for r in result.rows if r.ticker == "ZZZNOPE")
    assert zzz.error is not None
    aaa = next(r for r in result.rows if r.ticker == "AAA")
    assert aaa.error is None
    assert aaa.company_name == "Alpha Corp"


def test_too_few_tickers_raises(mocked_market_data):
    with pytest.raises(ValueError):
        compare_stocks(["AAA"])


def test_too_many_tickers_raises(mocked_market_data):
    with pytest.raises(ValueError):
        compare_stocks([f"T{i}" for i in range(MAX_TICKERS + 1)])


def test_duplicate_tickers_raises(mocked_market_data):
    with pytest.raises(ValueError):
        compare_stocks(["AAA", "AAA"])


def test_min_max_ticker_boundaries_are_two_and_eight():
    assert MIN_TICKERS == 2
    assert MAX_TICKERS == 8


def test_relative_strength_periods_populated_when_benchmark_available(mocked_market_data):
    result = compare_stocks(["AAA", "BBB"], benchmark_ticker="AAA")
    aaa = next(r for r in result.rows if r.ticker == "AAA")
    # AAA compared against itself as its own benchmark - relative return should be ~0.
    assert aaa.return_1y_percent is not None


def test_benchmark_unavailable_does_not_crash_comparison(monkeypatch, mocked_market_data):
    from app.comparison import service as comparison_module

    # Patch get_full_daily_history to fail only for the benchmark ticker,
    # succeeding (via the existing mock) for the real comparison tickers.
    original = comparison_module.market_data.get_full_daily_history

    def selective(ticker):
        if ticker == "SPY":
            raise comparison_module.market_data.DataUnavailableError(ticker)
        return original(ticker)

    monkeypatch.setattr(comparison_module.market_data, "get_full_daily_history", selective)

    result = compare_stocks(["AAA", "BBB"], benchmark_ticker="SPY")
    assert len(result.rows) == 2
    for r in result.rows:
        assert r.return_1y_percent is None
