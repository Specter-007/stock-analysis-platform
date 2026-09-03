from __future__ import annotations

from fastapi import APIRouter, Query

from app.config import (
    DEFAULT_FUNDAMENTAL_WEIGHT,
    DEFAULT_TECHNICAL_WEIGHT,
    DISCLAIMER,
    MARKET_REGIME_BENCHMARK,
    MIN_HISTORY_FOR_PARTIAL_INDICATORS,
    MODEL_VERSION_CURRENT,
    SIGNAL_HISTORY_LOOKBACK_SESSIONS,
    SIGNAL_PERFORMANCE_LOOKBACK_SESSIONS,
    SIGNAL_TIMEFRAME_DAILY,
    SUPPORTED_MODEL_VERSIONS,
)
from app.fundamentals import score as fundamental_score_module
from app.fundamentals.service import extract_fundamentals
from app.indicators import interpret
from app.indicators.compute import compute_indicator_frame, safe_float
from app.market.relative_strength import compute_relative_strength
from app.market.sector import compare_sector
from app.models.schemas import (
    Candle,
    ConfidenceModel,
    FundamentalMetricModel,
    FundamentalScoreFactorModel,
    FundamentalsResponse,
    HistoryResponse,
    IndicatorValue,
    OverallScoreModel,
    OverviewData,
    RelativeStrengthPeriodModel,
    RelativeStrengthResponse,
    RiskModel,
    ScoreFactorModel,
    SectorComparisonResponse,
    SectorPeerReturnModel,
    SignalChangeModel,
    SignalHistoryPointModel,
    SignalHistoryResponse,
    SignalPerformanceGroupModel,
    SignalPerformanceHorizonModel,
    SignalPerformanceResponse,
    SignalResponse,
    SignalStabilityModel,
    StockOverviewResponse,
    TechnicalResponse,
)
from app.services import market_data
from app.services.exceptions import InsufficientHistoryError
from app.signals import confidence as confidence_module
from app.signals import engine as signal_engine
from app.signals import history as history_module
from app.signals import invalidation as invalidation_module
from app.signals import performance as performance_module
from app.signals import risk as risk_module
from app.utils import timeutils
from app.utils.validation import normalize_and_validate_ticker

router = APIRouter(prefix="/api/stock", tags=["stock"])


def _require_min_history(ticker: str, df) -> None:
    if len(df) < MIN_HISTORY_FOR_PARTIAL_INDICATORS:
        raise InsufficientHistoryError(ticker, len(df), MIN_HISTORY_FOR_PARTIAL_INDICATORS)


def _validate_model_version(model_version: str) -> str:
    if model_version not in SUPPORTED_MODEL_VERSIONS:
        return MODEL_VERSION_CURRENT
    return model_version


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
                open=safe_float(row.get("Open")),
                high=safe_float(row.get("High")),
                low=safe_float(row.get("Low")),
                close=safe_float(row.get("Close")),
                volume=safe_float(row.get("Volume")),
                sma_20=safe_float(row.get("SMA_20")),
                sma_50=safe_float(row.get("SMA_50")),
                sma_100=safe_float(row.get("SMA_100")),
                sma_200=safe_float(row.get("SMA_200")),
            )
            for idx, row in visible.iterrows()
        ]
    else:
        candles = [
            Candle(
                date=idx.isoformat(),
                open=safe_float(row.get("Open")),
                high=safe_float(row.get("High")),
                low=safe_float(row.get("Low")),
                close=safe_float(row.get("Close")),
                volume=safe_float(row.get("Volume")),
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


def _to_factor_model(f) -> ScoreFactorModel:
    return ScoreFactorModel(
        category=f.category,
        name=f.name,
        points=f.points,
        detail=f.detail,
        polarity=f.polarity,
        current_value=f.current_value,
        threshold_label=f.threshold_label,
    )


@router.get("/{ticker}/signal", response_model=SignalResponse)
def get_stock_signal(
    ticker: str,
    model_version: str = Query(default=MODEL_VERSION_CURRENT),
    include_overall_score: bool = Query(default=False),
    technical_weight: float = Query(default=DEFAULT_TECHNICAL_WEIGHT, ge=0, le=1),
    fundamental_weight: float = Query(default=DEFAULT_FUNDAMENTAL_WEIGHT, ge=0, le=1),
):
    ticker = normalize_and_validate_ticker(ticker)
    model_version = _validate_model_version(model_version)
    full_df, meta = market_data.get_full_daily_history(ticker)
    _require_min_history(ticker, full_df)

    indicator_df = compute_indicator_frame(full_df)
    result = signal_engine.evaluate(indicator_df, model_version=model_version)
    conf = confidence_module.compute_confidence(result)
    risk = risk_module.assess_risk(indicator_df, result)

    full_history = history_module.compute_signal_history_full(
        indicator_df, SIGNAL_HISTORY_LOOKBACK_SESSIONS, model_version
    )
    history_points = history_module.to_history_points(full_history)
    signal_change = history_module.detect_signal_change(full_history)
    stability_pct, recent_signals = history_module.compute_signal_stability(history_points)
    invalidation_conditions = invalidation_module.what_could_invalidate(result)

    overall_score_model = None
    if include_overall_score:
        info = market_data.fetch_info_raw(ticker)
        fundamentals = extract_fundamentals(info)
        fscore = fundamental_score_module.compute_fundamental_score(fundamentals)
        overall = fundamental_score_module.compute_overall_score(
            result.score, fscore.score, technical_weight, fundamental_weight
        )
        overall_score_model = OverallScoreModel(
            technical_score=result.score,
            fundamental_score=fscore.score,
            overall_score=overall,
            technical_weight=technical_weight,
            fundamental_weight=fundamental_weight,
            fundamental_factors=[
                FundamentalScoreFactorModel(
                    key=f.key, label=f.label, value=f.value, healthy=f.healthy, points=f.points, max_points=f.max_points
                )
                for f in fscore.factors
            ],
            methodology=fscore.methodology,
        )

    latest_candle_date = indicator_df.index[-1].date()
    now = timeutils.utc_now()
    today_ny = now.astimezone(timeutils.NY_TZ).date()
    market_stat = timeutils.market_status(now)
    is_complete = not (market_stat == "OPEN" and latest_candle_date == today_ny)

    return SignalResponse(
        ticker=ticker,
        model_version=result.model_version,
        signal=result.signal,
        score=result.score,
        score_breakdown=result.category_breakdown,
        confidence=ConfidenceModel(
            confidence_percent=conf.confidence_percent,
            completeness=conf.completeness,
            agreement=conf.agreement,
            stability_margin=conf.stability_margin,
            volatility_clarity=conf.volatility_clarity,
            methodology=conf.methodology,
        ),
        positive_factors=[_to_factor_model(f) for f in result.positive_factors],
        negative_factors=[_to_factor_model(f) for f in result.negative_factors],
        neutral_factors=[_to_factor_model(f) for f in result.neutral_factors],
        trend_classification=result.trend_classification,
        volatility_regime=result.volatility_regime,
        risk=RiskModel(
            risk_level=risk.risk_level,
            risk_score=risk.risk_score,
            risk_factors=risk.risk_factors,
            max_drawdown_percent=risk.max_drawdown_pct,
            atr_percent_of_price=risk.atr_pct_of_price,
        ),
        signal_change=(
            SignalChangeModel(
                date=signal_change.date,
                previous_signal=signal_change.previous_signal,
                current_signal=signal_change.current_signal,
                previous_score=signal_change.previous_score,
                current_score=signal_change.current_score,
                contributing_changes=signal_change.contributing_changes,
            )
            if signal_change
            else None
        ),
        stability=SignalStabilityModel(
            stability_percent=stability_pct,
            window_sessions=min(len(history_points), 10),
            recent_signals=recent_signals,
        ),
        invalidation_conditions=invalidation_conditions,
        overall_score=overall_score_model,
        signal_timeframe=SIGNAL_TIMEFRAME_DAILY,
        signal_generated_at=timeutils.to_iso(now),
        latest_candle_date=str(latest_candle_date),
        is_latest_candle_complete=is_complete,
        disclaimer=DISCLAIMER,
        meta=meta.to_dict(),
    )


@router.get("/{ticker}/signal-history", response_model=SignalHistoryResponse)
def get_signal_history(
    ticker: str,
    lookback_sessions: int = Query(default=SIGNAL_HISTORY_LOOKBACK_SESSIONS, ge=5, le=1000),
    model_version: str = Query(default=MODEL_VERSION_CURRENT),
):
    ticker = normalize_and_validate_ticker(ticker)
    model_version = _validate_model_version(model_version)
    full_df, meta = market_data.get_full_daily_history(ticker)
    _require_min_history(ticker, full_df)

    indicator_df = compute_indicator_frame(full_df)
    points = history_module.compute_signal_history(indicator_df, lookback_sessions, model_version)

    return SignalHistoryResponse(
        ticker=ticker,
        model_version=model_version,
        lookback_sessions=lookback_sessions,
        history=[SignalHistoryPointModel(date=p.date, signal=p.signal, score=p.score, model_version=p.model_version) for p in points],
        meta=meta.to_dict(),
    )


@router.get("/{ticker}/signal-performance", response_model=SignalPerformanceResponse)
def get_signal_performance(
    ticker: str,
    lookback_sessions: int = Query(default=SIGNAL_PERFORMANCE_LOOKBACK_SESSIONS, ge=60, le=3000),
    model_version: str = Query(default=MODEL_VERSION_CURRENT),
):
    ticker = normalize_and_validate_ticker(ticker)
    model_version = _validate_model_version(model_version)
    full_df, meta = market_data.get_full_daily_history(ticker)
    _require_min_history(ticker, full_df)

    indicator_df = compute_indicator_frame(full_df)
    groups = performance_module.compute_signal_performance(indicator_df, lookback_sessions, model_version=model_version)

    return SignalPerformanceResponse(
        ticker=ticker,
        model_version=model_version,
        lookback_sessions=lookback_sessions,
        groups=[
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
            for g in groups
        ],
        meta=meta.to_dict(),
    )


@router.get("/{ticker}/fundamentals", response_model=FundamentalsResponse)
def get_fundamentals(ticker: str):
    ticker = normalize_and_validate_ticker(ticker)
    info = market_data.fetch_info_raw(ticker)
    if not info or not (info.get("shortName") or info.get("longName")):
        from app.services.exceptions import TickerNotFoundError

        raise TickerNotFoundError(ticker)

    fundamentals = extract_fundamentals(info)
    from app.services.market_data import DataMeta

    meta = DataMeta(data_status="HISTORICAL", timeframe="Latest reported fundamentals")

    def to_models(metrics):
        return [FundamentalMetricModel(key=m.key, label=m.label, value=m.value, unit=m.unit) for m in metrics]

    return FundamentalsResponse(
        ticker=ticker,
        valuation=to_models(fundamentals.valuation),
        growth=to_models(fundamentals.growth),
        profitability=to_models(fundamentals.profitability),
        balance_sheet=to_models(fundamentals.balance_sheet),
        has_any_data=fundamentals.has_any_data,
        meta=meta.to_dict(),
    )


@router.get("/{ticker}/relative-strength", response_model=RelativeStrengthResponse)
def get_relative_strength(ticker: str, benchmark: str = Query(default=MARKET_REGIME_BENCHMARK)):
    ticker = normalize_and_validate_ticker(ticker)
    benchmark = normalize_and_validate_ticker(benchmark)

    ticker_df, meta = market_data.get_full_daily_history(ticker)
    benchmark_df, _ = market_data.get_full_daily_history(benchmark)

    periods = compute_relative_strength(ticker_df["Close"], benchmark_df["Close"])

    return RelativeStrengthResponse(
        ticker=ticker,
        benchmark=benchmark,
        periods=[
            RelativeStrengthPeriodModel(
                period=p.period,
                ticker_return_percent=p.ticker_return_percent,
                benchmark_return_percent=p.benchmark_return_percent,
                relative_return_pp=p.relative_return_pp,
                classification=p.classification,
            )
            for p in periods
        ],
        meta=meta.to_dict(),
    )


@router.get("/{ticker}/sector", response_model=SectorComparisonResponse)
def get_sector_comparison(ticker: str):
    ticker = normalize_and_validate_ticker(ticker)
    overview, meta = market_data.get_overview(ticker)
    sector = overview.get("sector")

    result = compare_sector(ticker, sector)

    return SectorComparisonResponse(
        ticker=ticker,
        sector=result.sector,
        period=result.period,
        peers=[SectorPeerReturnModel(symbol=p.symbol, return_percent=p.return_percent) for p in result.peers],
        available=result.available,
        meta=meta.to_dict(),
    )
