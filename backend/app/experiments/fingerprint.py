"""V5: deterministic experiment reproducibility fingerprint.

A fingerprint is a SHA-256 hash of the experiment's canonical configuration
- every field that determines what the experiment's result actually MEANS
(model version, universe, benchmark, dates, capital, costs, allocation,
rebalancing, constraints, and the specific validation procedures/parameters
requested). Two configs that are identical in every one of those fields
always produce the same fingerprint, regardless of when they were run or
what today's global model defaults happen to be; changing any one of them
always produces a different fingerprint.

Deliberately EXCLUDED from the hash: `name`, `notes`, `tags`, and result
data - these describe the experiment but are not part of what makes it
reproducible.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from app.experiments.models import ExperimentConfig

# Bumping this invalidates every previously-computed fingerprint - only do
# so if the set of fields that determine reproducibility actually changes.
FINGERPRINT_SCHEMA_VERSION = 1


def _canonical_config_dict(config: ExperimentConfig) -> dict:
    data = asdict(config)
    # Order-independent fields are normalized so that equivalent configs
    # (e.g. tickers supplied in a different order) fingerprint identically.
    data["tickers"] = sorted(data["tickers"])
    data["sensitivity_parameters"] = sorted(data["sensitivity_parameters"])
    data["_schema_version"] = FINGERPRINT_SCHEMA_VERSION
    return data


def compute_fingerprint(config: ExperimentConfig) -> str:
    canonical = _canonical_config_dict(config)
    canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest().upper()
    groups = [digest[i : i + 4] for i in range(0, 16, 4)]
    return "-".join(groups)


def fingerprints_match(config_a: ExperimentConfig, config_b: ExperimentConfig) -> bool:
    return compute_fingerprint(config_a) == compute_fingerprint(config_b)
