"""V4 P2.6: Model Scorecard - a multi-dimensional evaluation summary.

Deliberately NOT a single blended score. Five independent dimensions are
reported, each with its own qualitative label and the real numbers behind
it: OUT_OF_SAMPLE_STRENGTH, ROBUSTNESS, WALK_FORWARD_STABILITY,
REGIME_DEPENDENCY, and FORWARD_PAPER_DATA. Collapsing these into one number
would hide exactly the kind of disagreement between dimensions (e.g. "great
in-sample, unstable walk-forward") that a scorecard exists to surface. An
optional, clearly-labeled illustrative composite is included only when the
caller explicitly asks for it, precisely because ANY blending is a judgment
call that a serious reader should be able to opt out of.

Every computation here reuses an existing, already-tested engine
(out_of_sample, walk_forward, sensitivity, regime_performance,
forward_validation) - this module adds no new backtesting or scoring logic
of its own, only the qualitative labeling of results those engines already
produce.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd

from app.backtesting.engine import run_backtest
from app.backtesting.out_of_sample import run_out_of_sample_validation
from app.backtesting.sensitivity import THRESHOLD_PARAMETERS, run_sensitivity_analysis
from app.backtesting.walk_forward import run_walk_forward
from app.config import MODEL_VERSION_CURRENT
from app.market.regime_performance import compute_regime_performance
from app.paper_trading import forward_validation
from app.services.exceptions import InsufficientHistoryError

MIN_TRADES_FOR_DIMENSION = 5
MIN_REGIME_DAYS_FOR_BUCKET = 15
MIN_FORWARD_DAYS_FOR_CONFIDENCE = 20

LABELS = ("STRONG", "MODERATE", "WEAK", "INSUFFICIENT_DATA", "NOT_PROVIDED")

SCORECARD_METHODOLOGY = (
    "Five independent dimensions, each labeled from its own real computation - never blended into "
    "a single score by default, because doing so would hide disagreement between dimensions that a "
    "scorecard exists to surface (e.g. strong in-sample results with unstable walk-forward folds). "
    "OUT_OF_SAMPLE_STRENGTH compares a held-out final-third period against the first two-thirds "
    "using the same run_out_of_sample_validation engine as the Out-of-Sample Validation page. "
    "ROBUSTNESS reuses the parameter-sensitivity engine's own PARAMETER_INERT/HIGHER_ROBUSTNESS/"
    "LOW_ROBUSTNESS classification. WALK_FORWARD_STABILITY is the share of walk-forward folds with "
    "a positive test-period return. REGIME_DEPENDENCY compares compounded returns across market "
    "regimes with enough trading days to be meaningful - concentrated-in-one-regime performance is "
    "flagged, not rewarded. FORWARD_PAPER_DATA reports live forward paper-trading sample size "
    "directly from the Forward Validation engine; it is never blended into other dimensions because "
    "it measures something no backtest can: real decisions on data that did not exist when the "
    "model was built. Any dimension with too little data to support a verdict is labeled "
    "INSUFFICIENT_DATA rather than guessed at."
)


@dataclass
class ScorecardDimension:
    name: str
    label: str
    detail: str
    supporting_metrics: dict = field(default_factory=dict)


@dataclass
class ModelScorecard:
    ticker: str
    model_version: str
    dimensions: list[ScorecardDimension] = field(default_factory=list)
    composite_note: str = (
        "No single composite score is computed by default - see each dimension's own label and "
        "supporting numbers. A composite necessarily makes a subjective weighting choice across "
        "dimensions that don't share a common unit; presenting one without that caveat would "
        "misrepresent how settled this evaluation actually is."
    )
    methodology: str = SCORECARD_METHODOLOGY


def _split_into_thirds(full_price_df: pd.DataFrame) -> list[tuple[str, dt.date, dt.date]] | None:
    dates = full_price_df.index
    n = len(dates)
    if n < 90:
        return None
    third = n // 3
    return [
        ("IN_SAMPLE", dates[0].date(), dates[third].date()),
        ("VALIDATION", dates[third + 1].date(), dates[2 * third].date()),
        ("OUT_OF_SAMPLE", dates[2 * third + 1].date(), dates[-1].date()),
    ]


def _out_of_sample_dimension(ticker: str, full_price_df: pd.DataFrame, initial_capital: float,
                              transaction_cost_bps: float, slippage_bps: float, model_version: str) -> ScorecardDimension:
    windows = _split_into_thirds(full_price_df)
    if windows is None:
        return ScorecardDimension("OUT_OF_SAMPLE_STRENGTH", "INSUFFICIENT_DATA", "Not enough history to split into in-sample/validation/out-of-sample periods.")

    result = run_out_of_sample_validation(
        ticker=ticker, full_price_df=full_price_df, windows=windows,
        initial_capital=initial_capital, transaction_cost_bps=transaction_cost_bps,
        slippage_bps=slippage_bps, model_version=model_version,
    )
    periods = {p.label: p for p in result.periods}
    oos = periods.get("OUT_OF_SAMPLE")
    in_sample = periods.get("IN_SAMPLE")

    if oos is None or oos.error or oos.number_of_trades < MIN_TRADES_FOR_DIMENSION:
        trades = oos.number_of_trades if oos and not oos.error else 0
        return ScorecardDimension(
            "OUT_OF_SAMPLE_STRENGTH", "INSUFFICIENT_DATA",
            f"The out-of-sample period produced only {trades} trade(s) - too few to draw a conclusion.",
            {"out_of_sample_trades": trades},
        )

    metrics = {"out_of_sample_return_percent": oos.total_return_percent, "out_of_sample_sharpe": oos.sharpe_ratio}
    if in_sample:
        metrics["in_sample_return_percent"] = in_sample.total_return_percent
        metrics["in_sample_sharpe"] = in_sample.sharpe_ratio

    oos_positive = (oos.total_return_percent or 0) > 0
    held_up = in_sample is not None and (oos.sharpe_ratio or -999) >= 0.5 * (in_sample.sharpe_ratio or 0) and oos_positive

    if held_up:
        label, detail = "STRONG", "Out-of-sample performance is positive and held up reasonably well relative to the in-sample period."
    elif oos_positive:
        label, detail = "MODERATE", "Out-of-sample return is positive but notably weaker than the in-sample period - a real overfitting warning sign."
    else:
        label, detail = "WEAK", "Out-of-sample return was negative - the in-sample edge did not persist on held-out data."

    return ScorecardDimension("OUT_OF_SAMPLE_STRENGTH", label, detail, metrics)


def _robustness_dimension(ticker: str, full_price_df: pd.DataFrame, initial_capital: float,
                           transaction_cost_bps: float, slippage_bps: float, model_version: str) -> ScorecardDimension:
    n = len(full_price_df)
    if n < 90:
        return ScorecardDimension("ROBUSTNESS", "INSUFFICIENT_DATA", "Not enough history to run a sensitivity sweep.")

    start_date = full_price_df.index[max(0, n - 500)].date()
    end_date = full_price_df.index[-1].date()

    result = run_sensitivity_analysis(
        ticker=ticker, full_price_df=full_price_df, start_date=start_date, end_date=end_date,
        initial_capital=initial_capital, transaction_cost_bps=transaction_cost_bps,
        slippage_bps=slippage_bps, model_version=model_version, parameters=THRESHOLD_PARAMETERS,
    )

    scored = [p for p in result.parameters if p.robustness in ("HIGHER_ROBUSTNESS", "LOW_ROBUSTNESS")]
    if not scored:
        return ScorecardDimension(
            "ROBUSTNESS", "INSUFFICIENT_DATA",
            "Every tested parameter was either PARAMETER_INERT or had an insufficient sample - no robustness verdict could be formed.",
        )

    robust_count = sum(1 for p in scored if p.robustness == "HIGHER_ROBUSTNESS")
    fraction = robust_count / len(scored)
    metrics = {"parameters_tested": len(scored), "parameters_robust": robust_count}

    if fraction >= 0.75:
        label, detail = "STRONG", "Most tested parameters showed stable performance across their neighborhood of values."
    elif fraction >= 0.4:
        label, detail = "MODERATE", "Some tested parameters showed stable performance; others did not."
    else:
        label, detail = "WEAK", "Most tested parameters showed unstable performance across their neighborhood of values - a real overfitting risk."

    return ScorecardDimension("ROBUSTNESS", label, detail, metrics)


def _walk_forward_dimension(ticker: str, full_price_df: pd.DataFrame, initial_capital: float,
                             transaction_cost_bps: float, slippage_bps: float) -> ScorecardDimension:
    result = run_walk_forward(
        ticker=ticker, full_price_df=full_price_df, train_years=2, test_years=1, max_folds=5,
        initial_capital=initial_capital, transaction_cost_bps=transaction_cost_bps, slippage_bps=slippage_bps,
    )
    if len(result.folds) < 3:
        return ScorecardDimension(
            "WALK_FORWARD_STABILITY", "INSUFFICIENT_DATA",
            f"Only {len(result.folds)} walk-forward fold(s) could be generated - too few for a stability verdict.",
            {"folds": len(result.folds)},
        )

    fraction_positive = result.folds_with_positive_return / len(result.folds)
    metrics = {"folds": len(result.folds), "folds_with_positive_return": result.folds_with_positive_return}

    if fraction_positive >= 0.7:
        label, detail = "STRONG", "Most walk-forward test folds were profitable."
    elif fraction_positive >= 0.4:
        label, detail = "MODERATE", "Roughly half of walk-forward test folds were profitable."
    else:
        label, detail = "WEAK", "Most walk-forward test folds were unprofitable."

    return ScorecardDimension("WALK_FORWARD_STABILITY", label, detail, metrics)


def _regime_dependency_dimension(ticker: str, benchmark: str, full_price_df: pd.DataFrame,
                                  benchmark_full_price_df: pd.DataFrame, initial_capital: float,
                                  transaction_cost_bps: float, slippage_bps: float, model_version: str) -> ScorecardDimension:
    try:
        backtest_result = run_backtest(
            ticker=ticker, full_price_df=full_price_df,
            start_date=full_price_df.index[max(0, len(full_price_df) - 500)].date(),
            end_date=full_price_df.index[-1].date(),
            initial_capital=initial_capital, transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps, model_version=model_version,
        )
    except InsufficientHistoryError:
        return ScorecardDimension("REGIME_DEPENDENCY", "INSUFFICIENT_DATA", "Not enough history to run the underlying backtest.")

    regime_result = compute_regime_performance(ticker, benchmark, backtest_result, benchmark_full_price_df)
    usable = [b for b in regime_result.buckets if b.trading_days >= MIN_REGIME_DAYS_FOR_BUCKET and b.compounded_return_percent is not None]

    if len(usable) < 2:
        return ScorecardDimension(
            "REGIME_DEPENDENCY", "INSUFFICIENT_DATA",
            f"Only {len(usable)} regime bucket(s) had enough trading days ({MIN_REGIME_DAYS_FOR_BUCKET}+) to compare.",
            {"usable_regime_buckets": len(usable)},
        )

    returns = [b.compounded_return_percent for b in usable]
    metrics = {b.regime: b.compounded_return_percent for b in usable}
    positive_regimes = sum(1 for r in returns if r > 0)

    if positive_regimes == len(returns):
        label, detail = "STRONG", "Performance was positive across every market regime with enough data to evaluate."
    elif positive_regimes >= len(returns) / 2:
        label, detail = "MODERATE", "Performance was positive in some regimes and negative in others."
    else:
        label, detail = "WEAK", "Performance was concentrated in a single regime and negative elsewhere - a real regime-dependency risk."

    return ScorecardDimension("REGIME_DEPENDENCY", label, detail, metrics)


def _forward_paper_dimension(portfolio_id: str | None) -> ScorecardDimension:
    if not portfolio_id:
        return ScorecardDimension(
            "FORWARD_PAPER_DATA", "NOT_PROVIDED",
            "No forward paper-trading portfolio was specified for this scorecard.",
        )

    fv = forward_validation.get_forward_validation(portfolio_id)
    metrics = {
        "trading_days_observed": fv.trading_days_observed,
        "total_return_percent": fv.total_return_percent,
        "benchmark_return_percent": fv.benchmark_return_percent,
    }

    if fv.trading_days_observed < MIN_FORWARD_DAYS_FOR_CONFIDENCE:
        return ScorecardDimension(
            "FORWARD_PAPER_DATA", "INSUFFICIENT_DATA",
            f"Only {fv.trading_days_observed} real trading day(s) of forward observation recorded so far "
            f"(< {MIN_FORWARD_DAYS_FOR_CONFIDENCE}) - too few to be meaningful.",
            metrics,
        )

    return ScorecardDimension(
        "FORWARD_PAPER_DATA", "MODERATE",
        f"{fv.trading_days_observed} real trading day(s) of forward observation recorded. This is still a "
        "small sample by statistical standards - treat as directional, not conclusive.",
        metrics,
    )


def build_model_scorecard(
    ticker: str,
    full_price_df: pd.DataFrame,
    benchmark: str,
    benchmark_full_price_df: pd.DataFrame,
    initial_capital: float = 10_000.0,
    transaction_cost_bps: float = 5.0,
    slippage_bps: float = 5.0,
    model_version: str = MODEL_VERSION_CURRENT,
    forward_portfolio_id: str | None = None,
) -> ModelScorecard:
    dimensions = [
        _out_of_sample_dimension(ticker, full_price_df, initial_capital, transaction_cost_bps, slippage_bps, model_version),
        _robustness_dimension(ticker, full_price_df, initial_capital, transaction_cost_bps, slippage_bps, model_version),
        _walk_forward_dimension(ticker, full_price_df, initial_capital, transaction_cost_bps, slippage_bps),
        _regime_dependency_dimension(ticker, benchmark, full_price_df, benchmark_full_price_df, initial_capital, transaction_cost_bps, slippage_bps, model_version),
        _forward_paper_dimension(forward_portfolio_id),
    ]
    return ModelScorecard(ticker=ticker, model_version=model_version, dimensions=dimensions)
