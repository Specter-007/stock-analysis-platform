"""V5: PostgreSQL-backed (SQLAlchemy) persistence for experiments, scoped
per user.

Replaces the earlier JSON-file store (see docs/MIGRATION.md for the
one-time import of any pre-existing single-user JSON experiment data). The
`Experiment` dataclass and its `experiment_to_dict`/`_dict_to_experiment`
conversion are unchanged from the V5 JSON design - they are simply the
dict written to an ExperimentDB row's JSON columns now, instead of to a
`{id}.json` file - so every experiment's shape (config, results,
provenance, lifecycle, fingerprint) is preserved exactly.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.config import EXPERIMENT_ID_PREFIX
from app.experiments.models import (
    DataProvenance,
    Experiment,
    ExperimentConfig,
    ExperimentResults,
    ValidationOutcome,
)
from app.models_db.experiment import ExperimentDB


def new_experiment_id() -> str:
    return f"{EXPERIMENT_ID_PREFIX}_{uuid.uuid4().hex[:12]}"


def _experiment_to_dict(experiment: Experiment) -> dict:
    from dataclasses import asdict

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


def _row_to_dict(row: ExperimentDB) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "status": row.status,
        "config": row.config,
        "fingerprint": row.fingerprint,
        "notes": row.notes,
        "tags": row.tags,
        "results": row.results or None,
        "provenance": row.data_provenance,
        "error": row.error,
        "forward_portfolio_id": row.forward_portfolio_id,
        "reproduced_from": row.reproduced_from,
        "archived": row.archived,
    }


def save_experiment(db: Session, user_id: str, experiment: Experiment) -> None:
    payload = experiment_to_dict(experiment)
    row = db.get(ExperimentDB, experiment.id)
    if row is None:
        row = ExperimentDB(id=experiment.id, user_id=user_id)
        db.add(row)
    row.name = experiment.name
    row.created_at = experiment.created_at
    row.updated_at = experiment.updated_at
    row.status = experiment.status
    row.config = payload["config"]
    row.fingerprint = experiment.fingerprint
    row.notes = experiment.notes
    row.tags = list(experiment.tags)
    row.results = payload["results"] or {}
    row.data_provenance = payload["provenance"]
    row.error = experiment.error
    row.forward_portfolio_id = experiment.forward_portfolio_id
    row.reproduced_from = experiment.reproduced_from
    row.archived = experiment.archived
    db.commit()


def load_experiment(db: Session, user_id: str, experiment_id: str) -> Experiment | None:
    row = db.get(ExperimentDB, experiment_id)
    if row is None or row.user_id != user_id:
        return None
    return _dict_to_experiment(_row_to_dict(row))


def delete_experiment(db: Session, user_id: str, experiment_id: str) -> bool:
    row = db.get(ExperimentDB, experiment_id)
    if row is None or row.user_id != user_id:
        return False
    db.delete(row)
    db.commit()
    return True


def list_experiment_ids(db: Session, user_id: str) -> list[str]:
    rows = db.query(ExperimentDB.id).filter_by(user_id=user_id).order_by(ExperimentDB.id).all()
    return [r[0] for r in rows]


def list_experiments(db: Session, user_id: str) -> list[Experiment]:
    rows = db.query(ExperimentDB).filter_by(user_id=user_id).all()
    return [_dict_to_experiment(_row_to_dict(row)) for row in rows]
