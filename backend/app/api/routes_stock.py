from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Query

from app.config import DISCLAIMER, MIN_HISTORY_FOR_PARTIAL_INDICATORS, SIGNAL_TIMEFRAME_DAILY
from app.indicators import interpret
from app.indicators.compute import compute_indicator_frame
from app.models.schemas import (
    Candle,
    ConfidenceModel,
    HistoryResponse,
    IndicatorValue,
    OverviewData,
    RiskModel,
    ScoreFactorModel,
    SignalResponse,
    StockOverviewResponse,
    TechnicalResponse,
)
from app.services import market_data
from app.services.exceptions import InsufficientHistoryError
from app.signals import confidence as confidence_module
from app.signals import engine as signal_engine
from app.signals import risk as risk_module
from app.utils import timeutils
from app.utils.validation import normalize_and_validate_ticker

router = APIRouter(prefix="/api/stock", tags=["stock"])


def _require_min_history(ticker: str, df) -> None:
    if len(df) < MIN_HISTORY_FOR_PARTIAL_INDICATORS:
        raise InsufficientHistoryError(ticker, len(df), MIN_HISTORY_FOR_PARTIAL_INDICATORS)


@router.get("/{ticker}", response_model=StockOverviewResponse)
def get_stock_overview(ticker: str):
    ticker = normalize_and_validate_ticker(ticker)
    overview, meta = market_data.get_overview(ticker)
    return StockOverviewResponse(ticker=ticker, data=OverviewData(**overview), meta=meta.to_dict())


@router.get("/{ticker}/history", response_model=HistoryResponse)
def get_stock_history(ticker: str, range: str = Query(default="1Y", alias="range")):
    ticker = normalize_and_validate_ticker(ticker)
    range_key = range.upper()

    result = market_data.get_chart_history(ticker, range_key)

    if result.is_daily:
        full_with_sma = compute_indicator_frame(result.full_df)
        visible = full_with_sma.loc[full_with_sma.index.isin(result.visible_df.index)]
        candles = [
            Candle(
                date=str(idx.date()),
                open=_safe(row.get("Open")),
                high=_safe(row.get("High")),
                low=_safe(row.get("Low")),
                close=_safe(row.get("Close")),
                volume=_safe(row.get("Volume")),
                sma_20=_safe(row.get("SMA_20")),
                sma_50=_safe(row.get("SMA_50")),
                sma_100=_safe(row.get("SMA_100")),
                sma_200=_safe(row.get("SMA_200")),
            )
            for idx, row in visible.iterrows()
        ]
    else:
        candles = [
            Candle(
                date=idx.isoformat(),
                open=_safe(row.get("Open")),
                high=_safe(row.get("High")),
                low=_safe(row.get("Low")),
                close=_safe(row.get("Close")),
                volume=_safe(row.get("Volume")),
            )
            for idx, row in result.visible_df.iterrows()
        ]

    return HistoryResponse(
        ticker=ticker,
        range=range_key,
        is_daily=result.is_daily,
        candles=candles,
        meta=result.meta.to_dict(),
    )


def _safe(value):
    from app.indicators.compute import safe_float

    return safe_float(value)


@router.get("/{ticker}/technical", response_model=TechnicalResponse)
def get_stock_technical(ticker: str):
    ticker = normalize_and_validate_ticker(ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)
    _require_min_history(ticker, full_df)

    indicator_df = compute_indicator_frame(full_df)
    row = indicator_df.iloc[-1]

    from app.indicators.compute import classify_trend, classify_volatility_regime

    regime = classify_volatility_regime(indicator_df)

    return TechnicalResponse(
        ticker=ticker,
        latest_candle_date=str(indicator_df.index[-1].date()),
        trend_classification=classify_trend(row),
        volatility_regime=regime,
        trend=[IndicatorValue(**iv) for iv in interpret.build_trend_indicators(row)],
        momentum=[IndicatorValue(**iv) for iv in interpret.build_momentum_indicators(row)],
        volatility=[IndicatorValue(**iv) for iv in interpret.build_volatility_indicators(row, regime)],
        volume=[IndicatorValue(**iv) for iv in interpret.build_volume_indicators(row)],
        price_relationships=[IndicatorValue(**iv) for iv in interpret.build_price_relationship_indicators(row)],
        meta=meta.to_dict(),
    )


@router.get("/{ticker}/signal", response_model=SignalResponse)
def get_stock_signal(ticker: str):
    ticker = normalize_and_validate_ticker(ticker)
    full_df, meta = market_data.get_full_daily_history(ticker)
    _require_min_history(ticker, full_df)

    indicator_df = compute_indicator_frame(full_df)
    result = signal_engine.evaluate(indicator_df)
    conf = confidence_module.compute_confidence(result)
    risk = risk_module.assess_risk(indicator_df, result)

    latest_candle_date = indicator_df.index[-1].date()
    now = timeutils.utc_now()
    today_ny = now.astimezone(timeutils.NY_TZ).date()
    market_stat = timeutils.market_status(now)
    is_complete = not (market_stat == "OPEN" and latest_candle_date == today_ny)

    def to_factor_model(f):
        return ScoreFactorModel(category=f.category, name=f.name, points=f.points, detail=f.detail, polarity=f.polarity)

    return SignalResponse(
        ticker=ticker,
        signal=result.signal,
        score=result.score,
        confidence=ConfidenceModel(
            confidence_percent=conf.confidence_percent,
            completeness=conf.completeness,
            agreement=conf.agreement,
            stability_margin=conf.stability_margin,
            volatility_clarity=conf.volatility_clarity,
            methodology=conf.methodology,
        ),
        positive_factors=[to_factor_model(f) for f in result.positive_factors],
        negative_factors=[to_factor_model(f) for f in result.negative_factors],
        neutral_factors=[to_factor_model(f) for f in result.neutral_factors],
        trend_classification=result.trend_classification,
        volatility_regime=result.volatility_regime,
        risk=RiskModel(
            risk_level=risk.risk_level,
            risk_score=risk.risk_score,
            risk_factors=risk.risk_factors,
            max_drawdown_percent=risk.max_drawdown_pct,
            atr_percent_of_price=risk.atr_pct_of_price,
        ),
        signal_timeframe=SIGNAL_TIMEFRAME_DAILY,
        signal_generated_at=timeutils.to_iso(now),
        latest_candle_date=str(latest_candle_date),
        is_latest_candle_complete=is_complete,
        disclaimer=DISCLAIMER,
        meta=meta.to_dict(),
    )
