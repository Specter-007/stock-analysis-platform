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
    EXPERIMENT_COMPARE_MAX,
    EXPERIMENT_COMPARE_MIN,
    MODEL_VERSION_CURRENT,
    PAPER_TRADING_DEFAULT_MAX_POSITION_PERCENT,
    SUPPORTED_MODEL_VERSIONS,
)


class DataMeta(BaseModel):
    data_source: str
    data_status: str
    retrieved_at: str
    latest_market_timestamp: str | None = None
    market_status: str | None = None
    timeframe: str
    data_quality: dict | None = None


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
    advanced_metrics: dict
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
    drawdown_threshold_percent: float = Field(default=-20.0, le=0, ge=-100)


class MonteCarloResponse(BaseModel):
    ticker: str
    simulations: int
    resampling_basis: str
    resampling_method: str
    sample_size: int
    seed: int | None
    median_return_percent: float | None
    percentile_5_return_percent: float | None
    percentile_95_return_percent: float | None
    median_max_drawdown_percent: float | None
    worst_max_drawdown_percent: float | None
    median_cagr_percent: float | None
    percentile_5_cagr_percent: float | None
    percentile_95_cagr_percent: float | None
    median_final_equity: float | None
    percentile_5_final_equity: float | None
    percentile_95_final_equity: float | None
    probability_of_loss_percent: float | None
    drawdown_threshold_percent: float
    probability_of_exceeding_drawdown_threshold_percent: float | None
    methodology: str
    meta: DataMeta


# ----------------------------------------------------- Portfolio Backtest

class PortfolioConstraintsModel(BaseModel):
    max_position_weight_percent: float = Field(default=100.0, gt=0, le=100)
    min_position_weight_percent: float = Field(default=0.0, ge=0, le=100)
    max_holdings: int | None = Field(default=None, gt=0)
    cash_allocation_percent: float = Field(default=0.0, ge=0, lt=100)
    sector_cap_percent: float | None = Field(default=None, gt=0, le=100)


class PortfolioBacktestRequest(BaseModel):
    tickers: list[str] = Field(min_length=2, max_length=20)
    start_date: dt.date
    end_date: dt.date
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    transaction_cost_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    allocation_method: str = Field(default="EQUAL_WEIGHT")
    rebalance_frequency: str = Field(default="MONTHLY")
    constraints: PortfolioConstraintsModel = Field(default_factory=PortfolioConstraintsModel)
    fixed_weights: dict[str, float] | None = None
    model_version: str = Field(default=MODEL_VERSION_CURRENT)
    benchmark_ticker: str | None = Field(default=DEFAULT_BENCHMARK_TICKER)

    @field_validator("model_version")
    @classmethod
    def valid_model_version_portfolio(cls, v: str) -> str:
        if v not in SUPPORTED_MODEL_VERSIONS:
            return MODEL_VERSION_CURRENT
        return v

    @field_validator("end_date")
    @classmethod
    def end_after_start_portfolio(cls, v: dt.date, info):
        start = info.data.get("start_date")
        if start is not None and v <= start:
            raise ValueError("end_date must be after start_date.")
        return v


class PortfolioEquityPointModel(BaseModel):
    date: str
    equity: float


class PortfolioHoldingSnapshotModel(BaseModel):
    date: str
    ticker: str
    weight_percent: float
    shares: float
    price: float
    market_value: float


class PortfolioBacktestResponse(BaseModel):
    tickers: list[str]
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    allocation_method: str
    rebalance_frequency: str
    total_return_percent: float | None
    equal_weight_buy_hold_return_percent: float | None
    benchmark_ticker: str | None
    benchmark_return_percent: float | None
    max_drawdown_percent: float | None
    sharpe_ratio: float | None
    trading_days: int
    number_of_rebalances: int
    equity_curve: list[PortfolioEquityPointModel]
    equal_weight_buy_hold_curve: list[PortfolioEquityPointModel]
    benchmark_curve: list[PortfolioEquityPointModel]
    drawdown_curve: list[PortfolioEquityPointModel]
    holdings_history: list[PortfolioHoldingSnapshotModel]
    advanced_metrics: dict
    risk_analytics: dict
    warnings: list[str]
    excluded_tickers: dict[str, str]
    methodology: dict[str, str]
    meta: DataMeta


# -------------------------------------------------------- Cost Stress (V5)

class CostStressRequest(BaseModel):
    ticker: str
    start_date: dt.date
    end_date: dt.date
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    base_commission_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    base_slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    model_version: str = Field(default=MODEL_VERSION_CURRENT)

    @field_validator("model_version")
    @classmethod
    def valid_model_version_cost_stress(cls, v: str) -> str:
        if v not in SUPPORTED_MODEL_VERSIONS:
            return MODEL_VERSION_CURRENT
        return v

    @field_validator("end_date")
    @classmethod
    def end_after_start_cost_stress(cls, v: dt.date, info):
        start = info.data.get("start_date")
        if start is not None and v <= start:
            raise ValueError("end_date must be after start_date.")
        return v


class CostStressScenarioModel(BaseModel):
    label: str
    commission_bps: float
    slippage_bps: float
    net_return_percent: float | None
    total_cost_percent: float | None
    cagr_percent: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    max_drawdown_percent: float | None
    turnover_percent: float | None
    number_of_trades: int


class CostStressResponse(BaseModel):
    ticker: str
    gross_return_percent: float | None
    commission_scenarios: list[CostStressScenarioModel]
    slippage_scenarios: list[CostStressScenarioModel]
    methodology: str
    meta: DataMeta


# -------------------------------------------------------- Sensitivity

class SensitivityRequest(BaseModel):
    ticker: str
    start_date: dt.date
    end_date: dt.date
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    transaction_cost_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    model_version: str = Field(default=MODEL_VERSION_CURRENT)
    # None preserves V3 behavior (buy_threshold + sell_threshold only). Pass an
    # explicit list - e.g. ["rsi_period", "sma_short"] - to sweep indicator
    # periods too. Unknown names are silently dropped rather than erroring, so
    # a typo degrades to "fewer parameters tested" instead of a 422.
    parameters: list[str] | None = Field(default=None)

    @field_validator("model_version")
    @classmethod
    def valid_model_version_sens(cls, v: str) -> str:
        if v not in SUPPORTED_MODEL_VERSIONS:
            return MODEL_VERSION_CURRENT
        return v

    @field_validator("end_date")
    @classmethod
    def end_after_start_sens(cls, v: dt.date, info):
        start = info.data.get("start_date")
        if start is not None and v <= start:
            raise ValueError("end_date must be after start_date.")
        return v


class SensitivityPointModel(BaseModel):
    parameter: str
    value: float
    is_default: bool
    total_return_percent: float | None
    cagr_percent: float | None
    sharpe_ratio: float | None
    max_drawdown_percent: float | None
    number_of_trades: int


class SensitivityResultModel(BaseModel):
    parameter: str
    label: str
    default_value: float
    points: list[SensitivityPointModel]
    robustness: str
    robust_region_min: float | None
    robust_region_max: float | None
    best_value: float | None = None
    median_value: float | None = None
    worst_value: float | None = None
    note: str | None = None


class SensitivityResponse(BaseModel):
    ticker: str
    model_version: str
    parameters: list[SensitivityResultModel]
    methodology: str
    meta: DataMeta


class SensitivityHeatmapRequest(BaseModel):
    ticker: str
    start_date: dt.date
    end_date: dt.date
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    transaction_cost_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    model_version: str = Field(default=MODEL_VERSION_CURRENT)
    param_x: str = Field(default="buy_threshold")
    param_y: str = Field(default="rsi_period")
    metric: str = Field(default="cagr_percent")

    @field_validator("model_version")
    @classmethod
    def valid_model_version_heatmap(cls, v: str) -> str:
        if v not in SUPPORTED_MODEL_VERSIONS:
            return MODEL_VERSION_CURRENT
        return v

    @field_validator("end_date")
    @classmethod
    def end_after_start_heatmap(cls, v: dt.date, info):
        start = info.data.get("start_date")
        if start is not None and v <= start:
            raise ValueError("end_date must be after start_date.")
        return v


class SensitivityHeatmapCellModel(BaseModel):
    x_value: float
    y_value: float
    metric_value: float | None
    number_of_trades: int
    insufficient_sample: bool


class SensitivityHeatmapResponse(BaseModel):
    ticker: str
    param_x: str
    param_y: str
    metric: str
    cells: list[SensitivityHeatmapCellModel]
    methodology: str
    meta: DataMeta


# ------------------------------------------------------- Out-of-sample

class OutOfSampleRequest(BaseModel):
    ticker: str
    in_sample_start: dt.date
    in_sample_end: dt.date
    validation_start: dt.date
    validation_end: dt.date
    out_of_sample_start: dt.date
    out_of_sample_end: dt.date
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    transaction_cost_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    model_version: str = Field(default=MODEL_VERSION_CURRENT)

    @field_validator("model_version")
    @classmethod
    def valid_model_version_oos(cls, v: str) -> str:
        if v not in SUPPORTED_MODEL_VERSIONS:
            return MODEL_VERSION_CURRENT
        return v

    @field_validator("out_of_sample_end")
    @classmethod
    def periods_are_chronological_and_non_overlapping(cls, v: dt.date, info):
        data = info.data
        required = (
            "in_sample_start", "in_sample_end", "validation_start",
            "validation_end", "out_of_sample_start",
        )
        if not all(k in data for k in required):
            return v  # an earlier field already failed validation
        ordering = [
            data["in_sample_start"], data["in_sample_end"],
            data["validation_start"], data["validation_end"],
            data["out_of_sample_start"], v,
        ]
        if ordering != sorted(ordering) or len(set(ordering)) != len(ordering):
            raise ValueError(
                "Periods must be strictly chronological and non-overlapping: "
                "in_sample_start < in_sample_end <= validation_start < validation_end "
                "<= out_of_sample_start < out_of_sample_end."
            )
        return v


class PeriodResultModel(BaseModel):
    label: str
    start_date: str
    end_date: str
    trading_days: int
    total_return_percent: float | None
    cagr_percent: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    max_drawdown_percent: float | None
    number_of_trades: int
    win_rate_percent: float | None
    buy_hold_return_percent: float | None
    error: str | None


class OutOfSampleResponse(BaseModel):
    ticker: str
    model_version: str
    periods: list[PeriodResultModel]
    methodology: str = (
        "All three periods are evaluated with the SAME fixed, non-fitted signal model - "
        "there is no parameter-training step. The value of this split is procedural: it "
        "forces an explicit, pre-committed boundary so the out-of-sample period's result "
        "was not visible while forming an opinion of the strategy."
    )
    meta: DataMeta


# ----------------------------------------------------------- Paper trading

class PaperTradeRequest(BaseModel):
    portfolio_id: str = Field(default="default", max_length=64)
    ticker: str
    action: str  # "BUY" | "SELL"
    shares: float | None = Field(default=None, gt=0)
    # Position sizing (BUY only; ignored for SELL). If `shares` is given it
    # always wins - these are only consulted when `shares` is omitted.
    sizing_mode: str | None = None  # "FIXED_SHARES" | "FIXED_CAPITAL_PERCENT" | "RISK_PERCENT"
    capital_percent: float | None = Field(default=None, gt=0, le=100)
    risk_percent: float | None = Field(default=None, gt=0, le=100)
    max_position_percent: float = Field(default=PAPER_TRADING_DEFAULT_MAX_POSITION_PERCENT, gt=0, le=100)
    # Optional risk controls attached to a new BUY position.
    stop_loss_percent: float | None = Field(default=None, gt=0, le=100)
    take_profit_percent: float | None = Field(default=None, gt=0)
    trailing_stop_percent: float | None = Field(default=None, gt=0, le=100)

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
    stop_loss_percent: float | None = None
    take_profit_percent: float | None = None
    trailing_stop_percent: float | None = None
    entry_signal: str | None = None
    entry_score: float | None = None
    entry_date: str | None = None


class PaperTradeModel(BaseModel):
    date: str
    ticker: str
    action: str
    shares: float
    price: float
    realized_pnl: float | None
    gross_pnl: float | None = None
    fees: float | None = None
    slippage: float | None = None
    net_pnl: float | None = None
    exit_reason: str | None = None
    entry_signal: str | None = None
    entry_score: float | None = None
    exit_signal: str | None = None
    exit_score: float | None = None
    model_version: str | None = None
    market_regime: str | None = None


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
    number_of_positions: int
    exposure_percent: float
    largest_position_percent: float
    cash_percent: float
    positions: list[PaperPositionModel]
    trades: list[PaperTradeModel]
    disclaimer: str = (
        "SIMULATION ONLY. No real money, no brokerage execution, no real orders. "
        "Position values use real live-retrieved market quotes; the trades themselves "
        "are purely virtual bookkeeping."
    )


class PaperRiskResponse(BaseModel):
    total_exposure_percent: float
    cash_percent: float
    largest_position_percent: float
    number_of_positions: int
    sector_concentration: dict[str, float]
    warnings: list[str]
    methodology: str


class PaperEquitySnapshotModel(BaseModel):
    date: str
    recorded_at: str
    equity: float
    cash: float
    invested_value: float
    realized_pnl: float
    unrealized_pnl: float
    cumulative_return_percent: float | None
    benchmark_value: float | None
    daily_pnl: float | None
    previous_snapshot_date: str | None


class ForwardValidationResponse(BaseModel):
    portfolio_id: str
    model_version: str
    model_version_is_mixed: bool
    start_date: str | None
    current_date: str | None
    trading_days_observed: int
    initial_capital: float
    current_equity: float
    total_return_percent: float
    benchmark_ticker: str | None
    benchmark_return_percent: float | None
    max_drawdown_percent: float | None
    number_of_trades: int
    open_positions_count: int
    realized_pnl: float
    unrealized_pnl: float
    insufficient_sample: bool
    warnings: list[str]
    methodology: str


class PaperEquityHistoryResponse(BaseModel):
    portfolio_id: str
    starting_capital: float
    benchmark_ticker: str | None
    snapshots: list[PaperEquitySnapshotModel]
    methodology: str = (
        "One immutable observation per real trading day the portfolio was actually queried on "
        "(keyed off the benchmark's own daily bars, never wall-clock date) - weekends, holidays, "
        "and days this portfolio was never viewed produce no entry rather than a fabricated one. "
        "daily_pnl is the change since the previous RECORDED observation, which may be more than "
        "one trading day earlier if the portfolio wasn't queried every day - see "
        "previous_snapshot_date on each entry. benchmark_value tracks what starting_capital would "
        "be worth invested in the benchmark on this portfolio's first recorded day."
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


# ---------------------------------------------------- Regime performance

class RegimePerformanceRequest(BaseModel):
    ticker: str
    benchmark: str = Field(default=DEFAULT_BENCHMARK_TICKER)
    start_date: dt.date
    end_date: dt.date
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    transaction_cost_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    model_version: str = Field(default=MODEL_VERSION_CURRENT)

    @field_validator("end_date")
    @classmethod
    def end_after_start_regime(cls, v: dt.date, info):
        start = info.data.get("start_date")
        if start is not None and v <= start:
            raise ValueError("end_date must be after start_date.")
        return v


class RegimeBucketModel(BaseModel):
    regime: str
    trading_days: int
    frequency_percent: float
    compounded_return_percent: float | None
    annualized_volatility_percent: float | None
    sharpe_ratio: float | None
    number_of_trades: int
    win_rate_percent: float | None


class RegimePerformanceResponse(BaseModel):
    ticker: str
    benchmark: str
    buckets: list[RegimeBucketModel]
    methodology: str
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


# ----------------------------------------------------------------- Watchlist

class WatchlistAddRequest(BaseModel):
    watchlist_id: str = Field(default="default", max_length=64)
    ticker: str


class WatchlistEntryModel(BaseModel):
    ticker: str
    company_name: str | None
    price: float | None
    change_percent: float | None
    signal: str | None
    score: float | None
    trend_classification: str | None
    market_regime: str | None
    data_status: str
    signal_changed_today: bool
    error: str | None = None


class WatchlistResponse(BaseModel):
    watchlist_id: str
    tickers: list[str]
    entries: list[WatchlistEntryModel]


# ---------------------------------------------------------------- Comparison

class ComparisonRequest(BaseModel):
    tickers: list[str] = Field(min_length=2, max_length=8)
    benchmark_ticker: str = Field(default=DEFAULT_BENCHMARK_TICKER)


class ComparisonRowModel(BaseModel):
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


class ComparisonResponse(BaseModel):
    tickers: list[str]
    benchmark_ticker: str
    rows: list[ComparisonRowModel]
    methodology: str


# ------------------------------------------------------------- Model Scorecard

class ScorecardRequest(BaseModel):
    ticker: str
    benchmark: str = Field(default=DEFAULT_BENCHMARK_TICKER)
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    transaction_cost_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    model_version: str = Field(default=MODEL_VERSION_CURRENT)
    forward_portfolio_id: str | None = Field(default=None)

    @field_validator("model_version")
    @classmethod
    def valid_model_version_scorecard(cls, v: str) -> str:
        if v not in SUPPORTED_MODEL_VERSIONS:
            return MODEL_VERSION_CURRENT
        return v


class ScorecardDimensionModel(BaseModel):
    name: str
    label: str
    detail: str
    supporting_metrics: dict


class ScorecardResponse(BaseModel):
    ticker: str
    model_version: str
    dimensions: list[ScorecardDimensionModel]
    composite_note: str
    methodology: str
    meta: DataMeta


# --------------------------------------------------------- Model Drift (V5)

class DriftRequest(BaseModel):
    ticker: str
    benchmark: str = Field(default=DEFAULT_BENCHMARK_TICKER)
    model_version: str = Field(default=MODEL_VERSION_CURRENT)

    @field_validator("model_version")
    @classmethod
    def valid_model_version_drift(cls, v: str) -> str:
        if v not in SUPPORTED_MODEL_VERSIONS:
            return MODEL_VERSION_CURRENT
        return v


class DistributionComparisonModel(BaseModel):
    dimension: str
    historical_percent: dict[str, float]
    recent_percent: dict[str, float]
    shifted_buckets: list[str]
    flagged: bool


class DriftResponse(BaseModel):
    ticker: str
    model_version: str
    historical_sessions: int
    recent_sessions: int
    insufficient_data: bool
    signal_distribution: DistributionComparisonModel | None
    factor_distribution: DistributionComparisonModel | None
    regime_distribution: DistributionComparisonModel | None
    methodology: str
    meta: DataMeta


# ------------------------------------------------------- Model vs Model

class ModelComparisonRequest(BaseModel):
    ticker: str
    start_date: dt.date
    end_date: dt.date
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    transaction_cost_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    benchmark_ticker: str | None = Field(default=DEFAULT_BENCHMARK_TICKER)
    forward_portfolio_id_v1: str | None = Field(default=None)
    forward_portfolio_id_v2: str | None = Field(default=None)

    @field_validator("end_date")
    @classmethod
    def end_after_start_model_comparison(cls, v: dt.date, info):
        start = info.data.get("start_date")
        if start is not None and v <= start:
            raise ValueError("end_date must be after start_date.")
        return v


class ModelVersionBacktestSummary(BaseModel):
    model_version: str
    total_return_percent: float | None
    cagr_percent: float | None
    sharpe_ratio: float | None
    max_drawdown_percent: float | None
    number_of_trades: int
    win_rate_percent: float | None


class ModelVersionForwardSummary(BaseModel):
    model_version: str
    portfolio_id: str
    trading_days_observed: int
    total_return_percent: float
    insufficient_sample: bool


class ModelComparisonResponse(BaseModel):
    ticker: str
    backtest_comparison: list[ModelVersionBacktestSummary]
    forward_comparison: list[ModelVersionForwardSummary]
    methodology: str
    meta: DataMeta


# ------------------------------------------------------ Experiment Lab (V5)

EXPERIMENT_DATA_MINING_METHODOLOGY = (
    "Each experiment's (ticker universe, date range) group count is shown so that repeatedly "
    "searching the same historical data for a better result is visible rather than hidden. This "
    "is disclosure, not a statistical correction: no p-value or significance test is applied "
    "automatically. Repeatedly testing variations on the same historical data increases the risk "
    "of overfitting/data-mining bias - use out-of-sample and walk-forward validation, and treat a "
    "\"best in-sample\" configuration as a hypothesis to re-test, not a conclusion."
)


class PortfolioConstraintsInput(BaseModel):
    max_position_weight_percent: float = Field(default=100.0, gt=0, le=100)
    min_position_weight_percent: float = Field(default=0.0, ge=0, le=100)
    max_holdings: int | None = Field(default=None, gt=0)
    cash_allocation_percent: float = Field(default=0.0, ge=0, lt=100)
    sector_cap_percent: float | None = Field(default=None, gt=0, le=100)


class ExperimentConfigModel(BaseModel):
    model_version: str = Field(default=MODEL_VERSION_CURRENT)
    tickers: list[str] = Field(min_length=1, max_length=20)
    benchmark: str = Field(default=DEFAULT_BENCHMARK_TICKER)
    start_date: dt.date
    end_date: dt.date
    initial_capital: float = Field(default=DEFAULT_INITIAL_CAPITAL, gt=0)
    commission_bps: float = Field(default=DEFAULT_TRANSACTION_COST_BPS, ge=0, le=1000)
    slippage_bps: float = Field(default=DEFAULT_SLIPPAGE_BPS, ge=0, le=1000)
    allocation_method: str | None = None
    rebalance_frequency: str | None = None
    portfolio_constraints: PortfolioConstraintsInput | None = None
    run_out_of_sample: bool = False
    run_walk_forward: bool = False
    run_sensitivity: bool = False
    run_monte_carlo: bool = False
    run_regime_analysis: bool = False
    run_cost_stress: bool = False
    monte_carlo_simulations: int = Field(default=1000, ge=100, le=5000)
    monte_carlo_seed: int | None = None
    sensitivity_parameters: list[str] = Field(default_factory=lambda: ["buy_threshold", "sell_threshold"])
    walk_forward_train_years: float = Field(default=2.0, gt=0, le=20)
    walk_forward_test_years: float = Field(default=1.0, gt=0, le=10)
    walk_forward_max_folds: int = Field(default=5, ge=1, le=20)

    @field_validator("model_version")
    @classmethod
    def valid_model_version_experiment(cls, v: str) -> str:
        if v not in SUPPORTED_MODEL_VERSIONS:
            return MODEL_VERSION_CURRENT
        return v

    @field_validator("end_date")
    @classmethod
    def end_after_start_experiment(cls, v: dt.date, info):
        start = info.data.get("start_date")
        if start is not None and v <= start:
            raise ValueError("end_date must be after start_date.")
        return v

    @field_validator("tickers")
    @classmethod
    def no_duplicate_tickers_experiment(cls, v: list[str]) -> list[str]:
        if len(set(t.upper() for t in v)) != len(v):
            raise ValueError("Duplicate tickers are not allowed.")
        return v


class CreateExperimentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    config: ExperimentConfigModel
    notes: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=20)


class ValidationOutcomeModel(BaseModel):
    requested: bool
    completed: bool
    error: str | None = None
    result: dict | None = None


class ExperimentResultsModel(BaseModel):
    backtest: ValidationOutcomeModel
    out_of_sample: ValidationOutcomeModel
    walk_forward: ValidationOutcomeModel
    sensitivity: ValidationOutcomeModel
    monte_carlo: ValidationOutcomeModel
    regime_performance: ValidationOutcomeModel
    cost_stress: ValidationOutcomeModel


class DataProvenanceModel(BaseModel):
    data_source: str
    retrieved_at: str
    data_status: str
    tickers_retrieved: list[str]
    tickers_unavailable: dict[str, str]
    latest_market_timestamp: str | None = None
    timeframe: str = "Daily"


class ExperimentResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    status: str
    config: ExperimentConfigModel
    fingerprint: str
    notes: str
    tags: list[str]
    results: ExperimentResultsModel | None = None
    data_provenance: DataProvenanceModel | None = None
    error: str | None = None
    forward_portfolio_id: str | None = None
    reproduced_from: str | None = None
    archived: bool = False


class ExperimentListRowModel(BaseModel):
    experiment: ExperimentResponse
    group_count: int
    data_mining_warning: bool


class ExperimentListResponse(BaseModel):
    experiments: list[ExperimentListRowModel]
    methodology: str = EXPERIMENT_DATA_MINING_METHODOLOGY


class DuplicateExperimentRequest(BaseModel):
    new_name: str | None = Field(default=None, max_length=200)


class ArchiveExperimentRequest(BaseModel):
    archived: bool = True


class UpdateExperimentNotesRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=5000)
    tags: list[str] | None = Field(default=None, max_length=20)


class CompareExperimentsRequest(BaseModel):
    experiment_ids: list[str] = Field(min_length=EXPERIMENT_COMPARE_MIN, max_length=EXPERIMENT_COMPARE_MAX)


class CompareExperimentsResponse(BaseModel):
    experiments: list[ExperimentResponse]
    warnings: list[str]


class ForwardVsHistoricalMetrics(BaseModel):
    return_percent: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown_percent: float | None = None
    trading_days_observed: int | None = None


class ForwardVsHistoricalResponse(BaseModel):
    available: bool
    reason: str | None
    historical: ForwardVsHistoricalMetrics | None
    historical_source: str | None
    forward: ForwardVsHistoricalMetrics | None
    forward_sample_developing: bool
    deviation_notes: list[str]


class PaperPortfolioSummaryModel(BaseModel):
    portfolio_id: str
    starting_capital: float
    current_value: float
    total_return_percent: float
    number_of_positions: int
    number_of_trades: int
    cash_percent: float


class PaperPortfolioListResponse(BaseModel):
    portfolios: list[PaperPortfolioSummaryModel]
