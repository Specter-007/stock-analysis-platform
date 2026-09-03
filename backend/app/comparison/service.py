"""Multi-ticker (2-8) side-by-side comparison.

Every field is sourced from the exact same functions the rest of the app
already uses and tests - `market_data.get_overview` / `get_full_daily_
history`, `compute_indicator_frame`, `signal_engine.evaluate`,
`extract_fundamentals`, and `compute_relative_strength`. This module adds
no new data-fetching or scoring logic of its own; it only fans a single
ticker's worth of already-verified logic out across several tickers
concurrently and assembles the results into one row per ticker.

A field that is genuinely unavailable for a given ticker is reported as
None ("N/A" in the UI) - never defaulted to 0. Zero is a real, meaningful
value (a real 0% margin, a real 0% return) that must never be confused
with "this data point could not be retrieved."

No cross-ticker normalization or ranking is performed - values are shown
side by side exactly as retrieved, so there is no scoring methodology to
document beyond "where did each number come from," which the per-row
fields' provenance already makes explicit.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from app.config import DEFAULT_BENCHMARK_TICKER, MODEL_VERSION_CURRENT
from app.fundamentals.service import extract_fundamentals
from app.indicators.compute import classify_trend, compute_indicator_frame, safe_float
from app.market.relative_strength import compute_relative_strength
from app.services import market_data
from app.signals import engine as signal_engine

MIN_TICKERS = 2
MAX_TICKERS = 8

COMPARISON_METHODOLOGY = (
    "Every field is retrieved independently per ticker from the same real-time/real-history data "
    "and the same deterministic signal engine used everywhere else in this app - no field is "
    "computed relative to the other tickers in the comparison, so there is no cross-ticker "
    "normalization or ranking to bias the numbers. A value that could not be retrieved or computed "
    "for a given ticker is shown as N/A, never as 0 - 0 is itself a meaningful real value (e.g. a "
    "genuine 0% margin) and must never be confused with missing data."
)


@dataclass
class ComparisonRow:
    ticker: str
    error: str | None = None
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    last_price: float | None = None
    change_percent: float | None = None
    market_cap: float | None = None
    trend_classification: str | None = None
    rsi_14: float | None = None
    dist_sma_50_pct: float | None = None
    dist_sma_200_pct: float | None = None
    historical_volatility_percent: float | None = None
    return_1m_percent: float | None = None
    return_3m_percent: float | None = None
    return_6m_percent: float | None = None
    return_1y_percent: float | None = None
    relative_strength_1y_classification: str | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    price_to_book: float | None = None
    revenue_growth_percent: float | None = None
    profit_margin_percent: float | None = None
    return_on_equity_percent: float | None = None
    signal: str | None = None
    score: float | None = None
    model_version: str | None = None


@dataclass
class ComparisonResult:
    tickers: list[str]
    benchmark_ticker: str
    rows: list[ComparisonRow] = field(default_factory=list)
    methodology: str = COMPARISON_METHODOLOGY


def _row_for_ticker(ticker: str, benchmark_close) -> ComparisonRow:
    try:
        overview, _ = market_data.get_overview(ticker)
    except Exception as exc:
        return ComparisonRow(ticker=ticker, error=str(exc))

    row = ComparisonRow(
        ticker=ticker,
        company_name=overview.get("company_name"),
        sector=overview.get("sector"),
        industry=overview.get("industry"),
        last_price=safe_float(overview.get("last_price")),
        change_percent=safe_float(overview.get("change_percent")),
        market_cap=safe_float(overview.get("market_cap")),
    )

    try:
        full_df, _ = market_data.get_full_daily_history(ticker)
        indicator_df = compute_indicator_frame(full_df)
        latest = indicator_df.iloc[-1]

        row.trend_classification = classify_trend(latest)
        row.rsi_14 = safe_float(latest.get("RSI_14"))
        row.dist_sma_50_pct = safe_float(latest.get("DIST_SMA_50_PCT"))
        row.dist_sma_200_pct = safe_float(latest.get("DIST_SMA_200_PCT"))
        # HIST_VOL_20 is already computed as a percentage (see
        # app.indicators.volatility.historical_volatility) - do not rescale it again.
        row.historical_volatility_percent = safe_float(latest.get("HIST_VOL_20"))

        if benchmark_close is not None:
            rs_periods = compute_relative_strength(full_df["Close"], benchmark_close)
            by_period = {p.period: p for p in rs_periods}
            if "1M" in by_period:
                row.return_1m_percent = by_period["1M"].ticker_return_percent
            if "3M" in by_period:
                row.return_3m_percent = by_period["3M"].ticker_return_percent
            if "6M" in by_period:
                row.return_6m_percent = by_period["6M"].ticker_return_percent
            if "1Y" in by_period:
                row.return_1y_percent = by_period["1Y"].ticker_return_percent
                row.relative_strength_1y_classification = by_period["1Y"].classification

        sig = signal_engine.evaluate(indicator_df)
        row.signal = sig.signal
        row.score = sig.score
        row.model_version = MODEL_VERSION_CURRENT
    except Exception:
        pass  # market/overview data still shown even if technical/model computation fails

    try:
        info = market_data.fetch_info_raw(ticker)
        fundamentals = extract_fundamentals(info)
        metrics_by_key = {m.key: m.value for section in (
            fundamentals.valuation, fundamentals.growth, fundamentals.profitability, fundamentals.balance_sheet
        ) for m in section}
        row.trailing_pe = metrics_by_key.get("trailing_pe")
        row.forward_pe = metrics_by_key.get("forward_pe")
        row.price_to_book = metrics_by_key.get("price_to_book")
        row.revenue_growth_percent = metrics_by_key.get("revenue_growth")
        row.profit_margin_percent = metrics_by_key.get("profit_margin")
        row.return_on_equity_percent = metrics_by_key.get("return_on_equity")
    except Exception:
        pass

    return row


def compare_stocks(tickers: list[str], benchmark_ticker: str = DEFAULT_BENCHMARK_TICKER) -> ComparisonResult:
    if not (MIN_TICKERS <= len(tickers) <= MAX_TICKERS):
        raise ValueError(f"Comparison requires between {MIN_TICKERS} and {MAX_TICKERS} tickers.")
    if len(set(tickers)) != len(tickers):
        raise ValueError("Duplicate tickers are not allowed in a comparison.")

    benchmark_close = None
    try:
        bench_df, _ = market_data.get_full_daily_history(benchmark_ticker)
        benchmark_close = bench_df["Close"]
    except Exception:
        benchmark_close = None

    with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as pool:
        rows = list(pool.map(lambda t: _row_for_ticker(t, benchmark_close), tickers))

    return ComparisonResult(tickers=tickers, benchmark_ticker=benchmark_ticker, rows=rows)
