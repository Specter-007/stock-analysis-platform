from __future__ import annotations

from fastapi import APIRouter, Query

from app.backtesting.engine import run_backtest
from app.config import (
    DISCLAIMER,
    MODEL_VERSION_CURRENT,
    MODEL_VERSION_NOTES,
    SCORE_BUY,
    SCORE_HOLD_LOW,
    SCORE_SELL_LOW,
    SCORE_STRONG_BUY,
    SIGNAL_HISTORY_LOOKBACK_SESSIONS,
    SIGNAL_PERFORMANCE_LOOKBACK_SESSIONS,
    SUPPORTED_MODEL_VERSIONS,
)
from app.indicators.compute import compute_indicator_frame
from app.models.schemas import ModelInfoResponse, ModelPerformanceResponse, SignalPerformanceGroupModel, SignalPerformanceHorizonModel, SignalStabilityModel
from app.services import market_data
from app.services.exceptions import InsufficientHistoryError
from app.signals import history as history_module
from app.signals import performance as performance_module
from app.utils.validation import normalize_and_validate_ticker

router = APIRouter(prefix="/api/model", tags=["model"])

FACTOR_WEIGHTS = [
    {"category": "Trend", "factor": "Price vs. 200-day SMA", "min": -15, "max": 15},
    {"category": "Trend", "factor": "50-day SMA vs. 200-day SMA", "min": -15, "max": 15},
    {"category": "Trend", "factor": "20-day SMA vs. 50-day SMA", "min": -10, "max": 10},
    {"category": "Momentum", "factor": "RSI (14) bucket", "min": -10, "max": 10},
    {"category": "Momentum", "factor": "MACD vs. signal / zero", "min": -15, "max": 15},
    {"category": "Momentum", "factor": "Rate of Change (12)", "min": -5, "max": 5},
    {"category": "Volume", "factor": "Volume confirmation", "min": -10, "max": 10},
    {"category": "Volatility", "factor": "Volatility regime", "min": -10, "max": 5},
]

DATA_LIMITATIONS = [
    "yfinance is an unofficial, community-maintained library - not an official Yahoo Finance API.",
    "Quote data during market hours is DELAYED (typically ~15 minutes), never claimed as real-time.",
    "Intraday history depth is limited by Yahoo Finance's own retention window.",
    "Some fundamental fields are occasionally missing or delayed for a given ticker.",
    "Rate limiting or transient outages are surfaced as DATA_UNAVAILABLE, never a fabricated fallback.",
]


@router.get("", response_model=ModelInfoResponse)
def get_model_info():
    return ModelInfoResponse(
        current_version=MODEL_VERSION_CURRENT,
        supported_versions=list(SUPPORTED_MODEL_VERSIONS),
        version_notes=dict(MODEL_VERSION_NOTES),
        factor_weights=FACTOR_WEIGHTS,
        score_thresholds={
            "strong_buy": SCORE_STRONG_BUY,
            "buy": SCORE_BUY,
            "hold_low": SCORE_HOLD_LOW,
            "sell_low": SCORE_SELL_LOW,
        },
        confidence_methodology=(
            "Weighted blend of data completeness (30%), factor agreement (40%), score "
            "stability margin (15%), and volatility clarity (15%), clamped to [5%, 97%]. "
            "NOT a probability of future returns."
        ),
        risk_methodology=(
            "Point-based risk score from volatility regime, RSI extremes, distance from "
            "the 200-day SMA, ATR as a percentage of price, factor conflicts, and historical "
            "maximum drawdown, mapped to LOW/MODERATE/HIGH/SEVERE."
        ),
        backtest_methodology={
            "signal_source": "Same deterministic engine as the live signal - no separate strategy.",
            "execution": "Signal calculated at candle close; execution at the next bar's open.",
            "position_model": "Long-or-flat only; no shorting.",
            "costs": "Transaction cost + slippage (bps) applied as a price haircut on every trade.",
        },
        no_look_ahead_methodology=(
            "Every indicator is a causal rolling/EWM computation - a value at row T never depends "
            "on rows after T. The backtester additionally enforces next-bar execution. Both "
            "properties are unit-tested directly (prefix-invariance and next-bar-execution tests)."
        ),
        data_limitations=DATA_LIMITATIONS,
        disclaimer=DISCLAIMER,
    )


@router.get("/performance", response_model=ModelPerformanceResponse)
def get_model_performance(
    ticker: str = Query(...),
    lookback_sessions: int = Query(default=SIGNAL_PERFORMANCE_LOOKBACK_SESSIONS, ge=60, le=3000),
):
    ticker = normalize_and_validate_ticker(ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)
    if len(full_df) < 60:
        raise InsufficientHistoryError(ticker, len(full_df), 60)

    indicator_df = compute_indicator_frame(full_df)

    full_history = history_module.compute_signal_history_full(indicator_df, lookback_sessions)
    history_points = history_module.to_history_points(full_history)

    signal_counts = {"STRONG_BUY": 0, "BUY": 0, "HOLD": 0, "SELL": 0, "STRONG_SELL": 0}
    for p in history_points:
        signal_counts[p.signal] = signal_counts.get(p.signal, 0) + 1

    stability_pct, recent_signals = history_module.compute_signal_stability(history_points)

    perf_groups = performance_module.compute_signal_performance(indicator_df, lookback_sessions)

    # A quick reference backtest over the same lookback window, for context.
    backtest_summary: dict = {}
    try:
        start_date = indicator_df.index[-min(lookback_sessions, len(indicator_df))].date()
        end_date = indicator_df.index[-1].date()
        bt = run_backtest(
            ticker=ticker,
            full_price_df=full_df,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10_000.0,
            transaction_cost_bps=5.0,
            slippage_bps=5.0,
        )
        backtest_summary = {
            "start_date": bt.start_date,
            "end_date": bt.end_date,
            "total_return_percent": bt.total_return_percent,
            "buy_hold_return_percent": bt.buy_hold_return_percent,
            "max_drawdown_percent": bt.max_drawdown_percent,
            "sharpe_ratio": bt.sharpe_ratio,
            "number_of_trades": bt.trade_stats.get("number_of_trades", 0),
        }
    except InsufficientHistoryError:
        backtest_summary = {"status": "insufficient_history_for_backtest"}

    return ModelPerformanceResponse(
        ticker=ticker,
        model_version=MODEL_VERSION_CURRENT,
        lookback_sessions=lookback_sessions,
        signal_counts=signal_counts,
        stability=SignalStabilityModel(
            stability_percent=stability_pct,
            window_sessions=min(len(history_points), 10),
            recent_signals=recent_signals,
        ),
        performance=[
            SignalPerformanceGroupModel(
                signal_group=g.signal_group,
                total_signals=g.total_signals,
                horizons=[
                    SignalPerformanceHorizonModel(
                        horizon_sessions=h.horizon_sessions,
                        sample_size=h.sample_size,
                        positive_rate_percent=h.positive_rate_percent,
                        average_return_percent=h.average_return_percent,
                        median_return_percent=h.median_return_percent,
                    )
                    for h in g.horizons
                ],
            )
            for g in perf_groups
        ],
        backtest_summary=backtest_summary,
        meta=meta.to_dict(),
    )
