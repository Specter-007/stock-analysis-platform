"""Fundamental data extraction from yfinance's `.info` payload.

Every field is read directly from Yahoo Finance's own reported values.
Nothing is estimated, interpolated, or invented - a field Yahoo doesn't
report for a given ticker is surfaced as `None` ("N/A" in the UI), never a
guessed number.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.indicators.compute import safe_float


@dataclass
class FundamentalMetric:
    key: str
    label: str
    value: float | None
    unit: str  # "x" | "%" | "$" | ""


@dataclass
class FundamentalsResult:
    valuation: list[FundamentalMetric]
    growth: list[FundamentalMetric]
    profitability: list[FundamentalMetric]
    balance_sheet: list[FundamentalMetric]
    has_any_data: bool


def _m(key: str, label: str, value, unit: str, pct: bool = False) -> FundamentalMetric:
    v = safe_float(value)
    if v is not None and pct:
        v = v * 100.0
    return FundamentalMetric(key=key, label=label, value=v, unit=unit)


def extract_fundamentals(info: dict) -> FundamentalsResult:
    valuation = [
        _m("trailing_pe", "Trailing P/E", info.get("trailingPE"), "x"),
        _m("forward_pe", "Forward P/E", info.get("forwardPE"), "x"),
        _m("peg_ratio", "PEG Ratio", info.get("trailingPegRatio") or info.get("pegRatio"), "x"),
        _m("price_to_sales", "Price / Sales", info.get("priceToSalesTrailing12Months"), "x"),
        _m("price_to_book", "Price / Book", info.get("priceToBook"), "x"),
    ]
    growth = [
        _m("revenue_growth", "Revenue Growth (YoY)", info.get("revenueGrowth"), "%", pct=True),
        _m("earnings_growth", "Earnings Growth (YoY)", info.get("earningsGrowth"), "%", pct=True),
    ]
    profitability = [
        _m("profit_margin", "Profit Margin", info.get("profitMargins"), "%", pct=True),
        _m("operating_margin", "Operating Margin", info.get("operatingMargins"), "%", pct=True),
        _m("return_on_equity", "Return on Equity", info.get("returnOnEquity"), "%", pct=True),
    ]
    balance_sheet = [
        # Yahoo Finance reports debtToEquity already scaled as a percentage
        # (e.g. 78.4 means a debt/equity RATIO of 0.784) - do not multiply again.
        _m("debt_to_equity", "Debt / Equity", info.get("debtToEquity"), "%"),
        _m("current_ratio", "Current Ratio", info.get("currentRatio"), "x"),
        _m("free_cash_flow", "Free Cash Flow", info.get("freeCashflow"), "$"),
    ]

    all_metrics = valuation + growth + profitability + balance_sheet
    has_any_data = any(m.value is not None for m in all_metrics)

    return FundamentalsResult(
        valuation=valuation,
        growth=growth,
        profitability=profitability,
        balance_sheet=balance_sheet,
        has_any_data=has_any_data,
    )
