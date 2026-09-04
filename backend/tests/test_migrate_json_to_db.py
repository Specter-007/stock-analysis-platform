"""Regression tests for scripts/migrate_json_to_db.py: legacy single-user
JSON data must import into the new user-owned Postgres schema with
verified record counts, never silently dropping data, and re-running must
never duplicate rows (idempotency).
"""
import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
migrate = importlib.import_module("migrate_json_to_db")

from app.models_db.experiment import ExperimentDB
from app.models_db.paper_trading import PaperPortfolioDB
from app.models_db.user import User
from app.models_db.watchlist import WatchlistDB


@pytest.fixture
def legacy_dirs(tmp_path, monkeypatch):
    watchlists = tmp_path / "watchlists"
    paper_trading = tmp_path / "paper_trading"
    experiments = tmp_path / "experiments"
    backups = tmp_path / "backups"
    for d in (watchlists, paper_trading, experiments):
        d.mkdir()
    monkeypatch.setattr(migrate, "WATCHLISTS_DIR", watchlists)
    monkeypatch.setattr(migrate, "PAPER_TRADING_DIR", paper_trading)
    monkeypatch.setattr(migrate, "EXPERIMENTS_DIR", experiments)
    monkeypatch.setattr(migrate, "BACKUP_ROOT", backups)
    return {"watchlists": watchlists, "paper_trading": paper_trading, "experiments": experiments, "backups": backups}


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_migration_imports_watchlists_and_portfolios(db_session, legacy_dirs, monkeypatch):
    _write_json(legacy_dirs["watchlists"] / "default.json", ["AAPL", "MSFT"])
    _write_json(
        legacy_dirs["paper_trading"] / "default.json",
        {"portfolio_id": "default", "starting_capital": 10000.0, "cash": 9000.0, "positions": {}, "trades": [], "equity_snapshots": [], "benchmark_basis": None},
    )
    monkeypatch.setattr(migrate, "SessionLocal", lambda: db_session)
    # SessionLocal is normally a context-free factory; db_session's own
    # lifecycle (close) is managed by the fixture, so make main()'s
    # `db.close()` a no-op for this shared test session.
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(sys, "argv", ["migrate_json_to_db.py"])

    exit_code = migrate.main()
    assert exit_code == 0

    owner = db_session.query(User).filter_by(email=migrate.LEGACY_DATA_OWNER_EMAIL).one()
    watchlist = db_session.query(WatchlistDB).filter_by(user_id=owner.id, slug="default").one()
    assert watchlist.tickers == ["AAPL", "MSFT"]
    portfolio = db_session.query(PaperPortfolioDB).filter_by(user_id=owner.id, slug="default").one()
    assert portfolio.state["cash"] == 9000.0

    backup_dirs = list(legacy_dirs["backups"].glob("pre_migration_*"))
    assert len(backup_dirs) == 1
    assert (backup_dirs[0] / "watchlists" / "default.json").exists()
    # Source files themselves must never be touched/deleted.
    assert (legacy_dirs["watchlists"] / "default.json").exists()


def test_migration_is_idempotent(db_session, legacy_dirs, monkeypatch):
    _write_json(legacy_dirs["watchlists"] / "default.json", ["AAPL"])
    monkeypatch.setattr(migrate, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(sys, "argv", ["migrate_json_to_db.py"])

    assert migrate.main() == 0
    assert migrate.main() == 0

    count = db_session.query(WatchlistDB).count()
    assert count == 1  # not duplicated by the second run


def test_migration_imports_experiments(db_session, legacy_dirs, monkeypatch):
    experiment_payload = {
        "id": "exp_abc123def456",
        "name": "Legacy experiment",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "status": "VALIDATED",
        "config": {
            "model_version": "1.1", "tickers": ["AAPL"], "benchmark": "SPY",
            "start_date": "2023-01-01", "end_date": "2024-01-01", "initial_capital": 10000.0,
            "commission_bps": 5.0, "slippage_bps": 5.0,
        },
        "fingerprint": "AAAA-BBBB-CCCC-DDDD",
        "notes": "",
        "tags": [],
        "results": None,
        "provenance": None,
        "error": None,
        "forward_portfolio_id": None,
        "reproduced_from": None,
        "archived": False,
    }
    _write_json(legacy_dirs["experiments"] / "exp_abc123def456.json", experiment_payload)
    monkeypatch.setattr(migrate, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(sys, "argv", ["migrate_json_to_db.py"])

    assert migrate.main() == 0

    owner = db_session.query(User).filter_by(email=migrate.LEGACY_DATA_OWNER_EMAIL).one()
    row = db_session.query(ExperimentDB).filter_by(id="exp_abc123def456").one()
    assert row.user_id == owner.id
    assert row.fingerprint == "AAAA-BBBB-CCCC-DDDD"


def test_migration_skips_corrupted_file_without_crashing(db_session, legacy_dirs, monkeypatch):
    (legacy_dirs["watchlists"] / "broken.json").write_text("{not valid json", encoding="utf-8")
    _write_json(legacy_dirs["watchlists"] / "good.json", ["TSLA"])
    monkeypatch.setattr(migrate, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(sys, "argv", ["migrate_json_to_db.py"])

    exit_code = migrate.main()
    assert exit_code == 1  # source count (2) exceeds imported count (1) -> reported as a mismatch, not silently OK

    owner = db_session.query(User).filter_by(email=migrate.LEGACY_DATA_OWNER_EMAIL).one()
    assert db_session.query(WatchlistDB).filter_by(user_id=owner.id, slug="good").count() == 1
    assert db_session.query(WatchlistDB).filter_by(user_id=owner.id, slug="broken").count() == 0


def test_dry_run_makes_no_database_changes(db_session, legacy_dirs, monkeypatch):
    _write_json(legacy_dirs["watchlists"] / "default.json", ["AAPL"])
    monkeypatch.setattr(migrate, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(sys, "argv", ["migrate_json_to_db.py", "--dry-run"])

    assert migrate.main() == 0
    assert db_session.query(User).count() == 0
    assert db_session.query(WatchlistDB).count() == 0
    assert not legacy_dirs["backups"].exists() or list(legacy_dirs["backups"].iterdir()) == []
