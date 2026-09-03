"""Pydantic response/request models. These are the API's public contract -
every field here is documented in the README's API section.
"""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field, field_validator

from app.config import (
    DEFAULT_BENCHMARK_TICKER,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_SLIPPAGE_BPS,
    DEFAULT_TRANSACTION_COST_BPS,
    MODEL_VERSION_CURRENT,
    SUPPORTED_MODEL_VERSIONS,
)


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
    current_value: float | None = None
    threshold_label: str = ""


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


class SignalChangeModel(BaseModel):
    date: str
    previous_signal: str
    current_signal: str
    previous_score: float
    current_score: float
    contributing_changes: list[str]


class SignalStabilityModel(BaseModel):
    stability_percent: float
    window_sessions: int
    recent_signals: list[str]  # most recent first
    methodology: str = (
        "Share of the most recent sessions whose signal matches the latest session's "
        "signal. Measures consistency of the model's own output over time - it is NOT "
        "a probability of any future return."
    )


class FundamentalScoreFactorModel(BaseModel):
    key: str
    label: str
    value: float | None
    healthy: bool | None
    points: float
    max_points: float


class OverallScoreModel(BaseModel):
    technical_score: float
    fundamental_score: float | None
    overall_score: float | None
    technical_weight: float
    fundamental_weight: float
    fundamental_factors: list[FundamentalScoreFactorModel]
    methodology: str


class SignalResponse(BaseModel):
    ticker: str
    model_version: str
    signal: str
    score: float
    score_breakdown: dict[str, float]
    confidence: ConfidenceModel
    positive_factors: list[ScoreFactorModel]
    negative_factors: list[ScoreFactorModel]
    neutral_factors: list[ScoreFactorModel]
    trend_classification: str
    volatility_regime: str
    risk: RiskModel
    signal_change: SignalChangeModel | None
    stability: SignalStabilityModel
    invalidation_conditions: list[str]
    overall_score: OverallScoreModel | None = None
    signal_timeframe: str
    signal_generated_at: str
    latest_candle_date: str
    is_latest_candle_complete: bool
    disclaimer: str
    meta: DataMeta


# --------------------------------------------------------- Signal History

class SignalHistoryPointModel(BaseModel):
    date: str
    signal: str
    score: float
    model_version: str


class SignalHistoryResponse(BaseModel):
    ticker: str
    model_version: str
    lookback_sessions: int
    history: list[SignalHistoryPointModel]
    meta: DataMeta


class SignalPerformanceHorizonModel(BaseModel):
    horizon_sessions: int
    sample_size: int
    positive_rate_percent: float | None
    average_return_percent: float | None
    median_return_percent: float | None


class SignalPerformanceGroupModel(BaseModel):
    signal_group: str
    total_signals: int
    horizons: list[SignalPerformanceHorizonModel]


class SignalPerformanceResponse(BaseModel):
    ticker: str
    model_version: str
    lookback_sessions: int
    groups: list[SignalPerformanceGroupModel]
    disclaimer: str = (
        "These are historical, retrospective outcome statistics for past signals on "
        "this ticker - not an accuracy score and not a prediction of future performance."
    )
    meta: DataMeta


# -------------------------------------------------------------- Fundamentals

class FundamentalMetricModel(BaseModel):
    key: str
    label: str
    value: float | None
    unit: str


class FundamentalsResponse(BaseModel):
    ticker: str
    valuation: list[FundamentalMetricModel]
    growth: list[FundamentalMetricModel]
    profitability: list[FundamentalMetricModel]
    balance_sheet: list[FundamentalMetricModel]
    has_any_data: bool
    meta: DataMeta


# ---------------------------------------------------------------- Market

class MarketRegimeResponse(BaseModel):
    benchmark: str
    regime: str
    trend_classification: str
    momentum: str
    volatility_regime: str
    regime_confidence_percent: float
    methodology: str
    meta: DataMeta


class RelativeStrengthPeriodModel(BaseModel):
    period: str
    ticker_return_percent: float | None
    benchmark_return_percent: float | None
    relative_return_pp: float | None
    classification: str


class RelativeStrengthResponse(BaseModel):
    ticker: str
    benchmark: str
    periods: list[RelativeStrengthPeriodModel]
    meta: DataMeta


class SectorPeerReturnModel(BaseModel):
    symbol: str
    return_percent: float | None


class SectorComparisonResponse(BaseModel):
    ticker: str
    sector: str | None
    period: str
    peers: list[SectorPeerReturnModel]
    available: bool
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
    model_version: str = Field(default=MODEL_VERSION_CURRENT)

    @field_validator("timeframe")
    @classmethod
    def only_daily_supported(cls, v: str) -> str:
        if v != "Daily":
            raise ValueError("Only the 'Daily' timeframe is currently supported for backtesting.")
        return v

    @field_validator("model_version")
    @classmethod
    def valid_model_version(cls, v: str) -> str:
        if v not in SUPPORTED_MODEL_VERSIONS:
            return MODEL_VERSION_CURRENT
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
    model_version: str
    meta: DataMeta


# ----------------------------------------------------------- Walk-forward

class WalkForwardRequest(BaseModel):
    ticker: str
    train_years: float = Field(default=2.0, gt=0, le=10)
    test_years: float = Field(default=1.0, gt=0, le=5)
    max_folds: int = Field(default=6, ge=1, le=8)
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    transaction_cost_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)


class WalkForwardFoldModel(BaseModel):
    fold_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    test_total_return_percent: float | None
    test_buy_hold_return_percent: float | None
    test_max_drawdown_percent: float | None
    test_sharpe_ratio: float | None
    test_number_of_trades: int
    test_win_rate_percent: float | None


class WalkForwardResponse(BaseModel):
    ticker: str
    train_years: float
    test_years: float
    folds: list[WalkForwardFoldModel]
    folds_with_positive_return: int
    average_test_return_percent: float | None
    methodology: str
    meta: DataMeta


# ------------------------------------------------------------- Monte Carlo

class MonteCarloRequest(BaseModel):
    ticker: str
    start_date: dt.date
    end_date: dt.date
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    transaction_cost_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    simulations: int = Field(default=1000, ge=100, le=5000)
    seed: int | None = None


class MonteCarloResponse(BaseModel):
    ticker: str
    simulations: int
    resampling_basis: str
    sample_size: int
    median_return_percent: float | None
    percentile_5_return_percent: float | None
    percentile_95_return_percent: float | None
    median_max_drawdown_percent: float | None
    worst_max_drawdown_percent: float | None
    methodology: str
    meta: DataMeta


# ----------------------------------------------------------- Paper trading

class PaperTradeRequest(BaseModel):
    portfolio_id: str = Field(default="default", max_length=64)
    ticker: str
    action: str  # "BUY" | "SELL"
    shares: float = Field(gt=0)

    @field_validator("action")
    @classmethod
    def valid_action(cls, v: str) -> str:
        if v.upper() not in ("BUY", "SELL"):
            raise ValueError("action must be 'BUY' or 'SELL'.")
        return v.upper()


class PaperPositionModel(BaseModel):
    ticker: str
    shares: float
    avg_entry_price: float
    current_price: float | None
    market_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_percent: float | None


class PaperTradeModel(BaseModel):
    date: str
    ticker: str
    action: str
    shares: float
    price: float
    realized_pnl: float | None


class PaperPortfolioResponse(BaseModel):
    portfolio_id: str
    simulation_only: bool = True
    starting_capital: float
    cash: float
    invested_capital: float
    current_value: float
    total_return_percent: float
    realized_pnl: float
    unrealized_pnl: float
    positions: list[PaperPositionModel]
    trades: list[PaperTradeModel]
    disclaimer: str = (
        "SIMULATION ONLY. No real money, no brokerage execution, no real orders. "
        "Position values use real live-retrieved market quotes; the trades themselves "
        "are purely virtual bookkeeping."
    )


# --------------------------------------------------------------- Model info

class ModelInfoResponse(BaseModel):
    current_version: str
    supported_versions: list[str]
    version_notes: dict[str, str]
    factor_weights: list[dict]
    score_thresholds: dict[str, float]
    confidence_methodology: str
    risk_methodology: str
    backtest_methodology: dict[str, str]
    no_look_ahead_methodology: str
    data_limitations: list[str]
    disclaimer: str


class ModelPerformanceResponse(BaseModel):
    ticker: str
    model_version: str
    lookback_sessions: int
    signal_counts: dict[str, int]
    stability: SignalStabilityModel
    performance: list[SignalPerformanceGroupModel]
    backtest_summary: dict[str, float | int | str | None]
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
