"""Pydantic response/request models. These are the API's public contract -
every field here is documented in the README's API section.
"""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field, field_validator

from app.config import DEFAULT_BENCHMARK_TICKER, DEFAULT_INITIAL_CAPITAL, DEFAULT_SLIPPAGE_BPS, DEFAULT_TRANSACTION_COST_BPS


class DataMeta(BaseModel):
    data_source: str
    data_status: str
    retrieved_at: str
    latest_market_timestamp: str | None = None
    market_status: str | None = None
    timeframe: str


# ---------------------------------------------------------------- Overview

class OverviewData(BaseModel):
    company_name: str
    exchange: str
    currency: str
    sector: str
    industry: str
    last_price: float | None
    previous_close: float | None
    change: float | None
    change_percent: float | None
    day_high: float | None
    day_low: float | None
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None
    market_cap: float | None
    volume: float | None
    average_volume: float | None
    website: str
    description: str


class StockOverviewResponse(BaseModel):
    ticker: str
    data: OverviewData
    meta: DataMeta


# ------------------------------------------------------------------ History

class Candle(BaseModel):
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_100: float | None = None
    sma_200: float | None = None


class HistoryResponse(BaseModel):
    ticker: str
    range: str
    is_daily: bool
    candles: list[Candle]
    meta: DataMeta


# --------------------------------------------------------------- Technical

class IndicatorValue(BaseModel):
    key: str
    label: str
    value: float | None
    unit: str = ""
    interpretation: str
    status: str  # "bullish" | "bearish" | "neutral" | "warning" | "unavailable"


class TechnicalResponse(BaseModel):
    ticker: str
    latest_candle_date: str
    trend_classification: str
    volatility_regime: str
    trend: list[IndicatorValue]
    momentum: list[IndicatorValue]
    volatility: list[IndicatorValue]
    volume: list[IndicatorValue]
    price_relationships: list[IndicatorValue]
    meta: DataMeta


# ------------------------------------------------------------------ Signal

class ScoreFactorModel(BaseModel):
    category: str
    name: str
    points: float
    detail: str
    polarity: str


class ConfidenceModel(BaseModel):
    confidence_percent: float
    completeness: float
    agreement: float
    stability_margin: float
    volatility_clarity: float
    methodology: str


class RiskModel(BaseModel):
    risk_level: str
    risk_score: int
    risk_factors: list[str]
    max_drawdown_percent: float | None
    atr_percent_of_price: float | None


class SignalResponse(BaseModel):
    ticker: str
    signal: str
    score: float
    confidence: ConfidenceModel
    positive_factors: list[ScoreFactorModel]
    negative_factors: list[ScoreFactorModel]
    neutral_factors: list[ScoreFactorModel]
    trend_classification: str
    volatility_regime: str
    risk: RiskModel
    signal_timeframe: str
    signal_generated_at: str
    latest_candle_date: str
    is_latest_candle_complete: bool
    disclaimer: str
    meta: DataMeta


# --------------------------------------------------------------- Backtest

class BacktestRequest(BaseModel):
    ticker: str
    start_date: dt.date
    end_date: dt.date
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    transaction_cost_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    benchmark_ticker: str | None = Field(default=DEFAULT_BENCHMARK_TICKER)
    timeframe: str = Field(default="Daily")

    @field_validator("timeframe")
    @classmethod
    def only_daily_supported(cls, v: str) -> str:
        if v != "Daily":
            raise ValueError("Only the 'Daily' timeframe is currently supported for backtesting.")
        return v

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: dt.date, info):
        start = info.data.get("start_date")
        if start is not None and v <= start:
            raise ValueError("end_date must be after start_date.")
        return v


class TradeModel(BaseModel):
    entry_date: str
    entry_price: float
    exit_date: str | None
    exit_price: float | None
    shares: float
    pnl: float | None
    pnl_pct: float | None


class EquityPointModel(BaseModel):
    date: str
    equity: float


class BacktestResponse(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_percent: float | None
    annualized_return_percent: float | None
    buy_hold_return_percent: float | None
    benchmark_ticker: str | None
    benchmark_return_percent: float | None
    max_drawdown_percent: float | None
    sharpe_ratio: float | None
    trading_days: int
    open_position_at_end: bool
    number_of_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_percent: float | None
    average_trade_percent: float | None
    best_trade_percent: float | None
    worst_trade_percent: float | None
    profit_factor: float | None
    trades: list[TradeModel]
    strategy_curve: list[EquityPointModel]
    buy_hold_curve: list[EquityPointModel]
    benchmark_curve: list[EquityPointModel]
    drawdown_curve: list[EquityPointModel]
    warnings: list[str]
    methodology: dict[str, str]
    meta: DataMeta


# -------------------------------------------------------------------- Misc

class SearchResultItem(BaseModel):
    symbol: str
    name: str
    exchange: str
    type: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    meta: DataMeta


class IndexQuote(BaseModel):
    symbol: str
    name: str
    last_price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    status: str


class MoverQuote(BaseModel):
    symbol: str
    last_price: float
    change: float
    change_percent: float


class MarketOverviewResponse(BaseModel):
    indexes: list[IndexQuote]
    gainers: list[MoverQuote]
    losers: list[MoverQuote]
    meta: DataMeta


class ErrorResponse(BaseModel):
    error_type: str
    detail: str
