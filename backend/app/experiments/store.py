"""V5: JSON-file-backed persistence for experiments.

Deliberately not a database, consistent with the paper-trading and
watchlist stores: one small JSON file per experiment
(`backend/data/experiments/{id}.json`, gitignored), durable across backend
restarts without introducing new infrastructure. Listing enumerates the
directory directly rather than maintaining a separate index file - simpler,
and impossible for an index to drift out of sync with the files it
describes.

Writes are atomic (write to a temp file, then os.replace) so a crash
mid-write can never leave a half-written, corrupted experiment file - a
reader always sees either the old complete version or the new complete
version, never a partial one.
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from dataclasses import asdict
from pathlib import Path

from app.config import EXPERIMENTS_DATA_DIR, EXPERIMENT_ID_PREFIX
from app.experiments.models import (
    DataProvenance,
    Experiment,
    ExperimentConfig,
    ExperimentResults,
    ValidationOutcome,
)

_LOCK = threading.Lock()
_DATA_DIR = Path(EXPERIMENTS_DATA_DIR)

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def new_experiment_id() -> str:
    return f"{EXPERIMENT_ID_PREFIX}_{uuid.uuid4().hex[:12]}"


def _path_for(experiment_id: str) -> Path:
    if not _SAFE_ID_RE.match(experiment_id):
        raise ValueError(f"Invalid experiment id: {experiment_id!r}")
    return _DATA_DIR / f"{experiment_id}.json"


def _experiment_to_dict(experiment: Experiment) -> dict:
    return asdict(experiment)


def _dict_to_experiment(data: dict) -> Experiment:
    config = ExperimentConfig(**data["config"])
    provenance = DataProvenance(**data["provenance"]) if data.get("provenance") else None
    results = None
    if data.get("results"):
        results = ExperimentResults(**{k: ValidationOutcome(**v) for k, v in data["results"].items()})
    return Experiment(
        id=data["id"],
        name=data["name"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        status=data["status"],
        config=config,
        fingerprint=data["fingerprint"],
        notes=data.get("notes", ""),
        tags=data.get("tags", []),
        results=results,
        data_provenance=provenance,
        error=data.get("error"),
        forward_portfolio_id=data.get("forward_portfolio_id"),
        reproduced_from=data.get("reproduced_from"),
        archived=data.get("archived", False),
    )


def experiment_to_dict(experiment: Experiment) -> dict:
    payload = _experiment_to_dict(experiment)
    payload["provenance"] = payload.pop("data_provenance", None)
    return payload


def save_experiment(experiment: Experiment) -> None:
    path = _path_for(experiment.id)
    payload = experiment_to_dict(experiment)

    with _LOCK:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp_path, path)


def load_experiment(experiment_id: str) -> Experiment | None:
    path = _path_for(experiment_id)
    with _LOCK:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return _dict_to_experiment(data)


def delete_experiment(experiment_id: str) -> bool:
    path = _path_for(experiment_id)
    with _LOCK:
        if not path.exists():
            return False
        path.unlink()
        return True


def list_experiment_ids() -> list[str]:
    with _LOCK:
        if not _DATA_DIR.exists():
            return []
        return sorted(p.stem for p in _DATA_DIR.glob("*.json"))


def list_experiments() -> list[Experiment]:
    experiments = []
    for exp_id in list_experiment_ids():
        exp = load_experiment(exp_id)
        if exp is not None:
            experiments.append(exp)
    return experiments
