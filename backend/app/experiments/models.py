"""V5: Experiment Lab data model.

An Experiment is a reproducible research configuration - it stores the
CONFIGURATION that produced a result, not just the final numbers, so a
past experiment can be inspected, reproduced, or compared long after
today's model defaults, thresholds, or cost assumptions have changed.

Lifecycle:

    DRAFT -> CONFIGURED -> RUNNING -> COMPLETED -> VALIDATED -> PAPER_FORWARD_TEST
                                          (or)-> FAILED

COMPLETED means the core backtest finished. VALIDATED means every
validation procedure the config actually requested (out-of-sample,
walk-forward, sensitivity, Monte Carlo, regime analysis, cost stress) also
completed without error - an experiment that only ran a backtest is never
called "validated" merely because the backtest succeeded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STATUS_DRAFT = "DRAFT"
STATUS_CONFIGURED = "CONFIGURED"
STATUS_RUNNING = "RUNNING"
STATUS_COMPLETED = "COMPLETED"
STATUS_VALIDATED = "VALIDATED"
STATUS_PAPER_FORWARD_TEST = "PAPER_FORWARD_TEST"
STATUS_FAILED = "FAILED"

ALL_STATUSES = (
    STATUS_DRAFT, STATUS_CONFIGURED, STATUS_RUNNING, STATUS_COMPLETED,
    STATUS_VALIDATED, STATUS_PAPER_FORWARD_TEST, STATUS_FAILED,
)


@dataclass
class ExperimentConfig:
    """Everything needed to reproduce an experiment's result. This is the
    part of an Experiment that becomes IMMUTABLE the moment the experiment
    is first run - later changes to global model defaults, thresholds, or
    cost assumptions must never retroactively change what this describes.
    """
    model_version: str
    tickers: list[str]
    benchmark: str
    start_date: str
    end_date: str
    initial_capital: float
    commission_bps: float
    slippage_bps: float
    allocation_method: str | None = None
    rebalance_frequency: str | None = None
    portfolio_constraints: dict[str, Any] | None = None
    run_out_of_sample: bool = False
    run_walk_forward: bool = False
    run_sensitivity: bool = False
    run_monte_carlo: bool = False
    run_regime_analysis: bool = False
    run_cost_stress: bool = False
    monte_carlo_simulations: int = 1000
    monte_carlo_seed: int | None = None
    sensitivity_parameters: list[str] = field(default_factory=lambda: ["buy_threshold", "sell_threshold"])
    walk_forward_train_years: float = 2.0
    walk_forward_test_years: float = 1.0
    walk_forward_max_folds: int = 5

    @property
    def is_portfolio(self) -> bool:
        return len(self.tickers) > 1


@dataclass
class DataProvenance:
    data_source: str
    retrieved_at: str
    data_status: str
    tickers_retrieved: list[str] = field(default_factory=list)
    tickers_unavailable: dict[str, str] = field(default_factory=dict)
    latest_market_timestamp: str | None = None
    timeframe: str = "Daily"


@dataclass
class ValidationOutcome:
    """Per-validation-procedure outcome, so a caller can tell "requested but
    failed" apart from "not requested" apart from "succeeded".
    """
    requested: bool = False
    completed: bool = False
    error: str | None = None
    result: dict[str, Any] | None = None


@dataclass
class ExperimentResults:
    backtest: ValidationOutcome = field(default_factory=ValidationOutcome)
    out_of_sample: ValidationOutcome = field(default_factory=ValidationOutcome)
    walk_forward: ValidationOutcome = field(default_factory=ValidationOutcome)
    sensitivity: ValidationOutcome = field(default_factory=ValidationOutcome)
    monte_carlo: ValidationOutcome = field(default_factory=ValidationOutcome)
    regime_performance: ValidationOutcome = field(default_factory=ValidationOutcome)
    cost_stress: ValidationOutcome = field(default_factory=ValidationOutcome)


@dataclass
class Experiment:
    id: str
    name: str
    created_at: str
    updated_at: str
    status: str
    config: ExperimentConfig
    fingerprint: str
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    results: ExperimentResults | None = None
    data_provenance: DataProvenance | None = None
    error: str | None = None
    forward_portfolio_id: str | None = None
    reproduced_from: str | None = None  # source experiment id, if created via "duplicate"/"reproduce"
    archived: bool = False
