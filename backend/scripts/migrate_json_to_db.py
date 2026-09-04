#!/usr/bin/env python
"""One-time migration: import pre-existing single-user JSON data (watchlists,
paper-trading portfolios, experiments) into the PostgreSQL-backed
(SQLAlchemy) schema, owned by a designated "legacy data owner" account.

This data predates multi-user accounts entirely - there is no user to
attribute it to, so per docs/MIGRATION.md this script does NOT guess. It
creates (or reuses) exactly one account, identified by the
LEGACY_DATA_OWNER_EMAIL environment variable (app.settings), and assigns
every legacy record to it. That account is created with a random,
never-printed, unusable password - to actually use it, run the normal
"forgot password" flow for its email address.

Safety:
  - Never deletes or modifies the source JSON files. Run 1: copies every
    JSON directory this app writes to (watchlists, paper_trading,
    experiments) into a timestamped backup before touching the database.
  - Idempotent: re-running is always safe. Watchlists/portfolios upsert by
    (user, slug); experiments upsert by their existing id. No duplicates
    are ever created by running this twice.
  - Verifies record counts (source file count vs. resulting DB row count
    for the legacy owner) and prints an explicit report - it does not
    silently declare success.

Usage (from the backend/ directory, with DATABASE_URL pointing at an
already-migrated - `alembic upgrade head` - database):

    python scripts/migrate_json_to_db.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.security import hash_password  # noqa: E402
from app.config import EXPERIMENTS_DATA_DIR, PAPER_TRADING_DATA_DIR  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.experiments.store import _dict_to_experiment  # noqa: E402
from app.experiments import store as experiments_store  # noqa: E402
from app.models_db.experiment import ExperimentDB  # noqa: E402
from app.models_db.paper_trading import PaperPortfolioDB  # noqa: E402
from app.models_db.user import User  # noqa: E402
from app.models_db.watchlist import WatchlistDB  # noqa: E402
from app.paper_trading import store as paper_trading_store  # noqa: E402
from app.settings import LEGACY_DATA_OWNER_EMAIL  # noqa: E402
from app.watchlist import store as watchlist_store  # noqa: E402

WATCHLISTS_DIR = Path("data/watchlists")
PAPER_TRADING_DIR = Path(PAPER_TRADING_DATA_DIR)
EXPERIMENTS_DIR = Path(EXPERIMENTS_DATA_DIR)

BACKUP_ROOT = Path("data/backups")


def _backup_json_directories() -> Path | None:
    # Microsecond resolution: two invocations within the same second (e.g.
    # back-to-back test runs, or a quick retry) must never collide on the
    # same backup directory name.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = BACKUP_ROOT / f"pre_migration_{timestamp}"
    any_copied = False
    for src in (WATCHLISTS_DIR, PAPER_TRADING_DIR, EXPERIMENTS_DIR):
        if src.exists() and any(src.iterdir()):
            dest = backup_dir / src.name
            shutil.copytree(src, dest)
            any_copied = True
    if not any_copied:
        return None
    return backup_dir


def _get_or_create_legacy_owner(db, dry_run: bool) -> User:
    owner = db.query(User).filter_by(email=LEGACY_DATA_OWNER_EMAIL).one_or_none()
    if owner is not None:
        print(f"Legacy data owner already exists: {owner.email} (id={owner.id})")
        return owner

    print(f"Creating legacy data owner account: {LEGACY_DATA_OWNER_EMAIL}")
    print(
        "  This account is created with a random, unusable password. To sign into it, "
        "use the password-reset flow (POST /api/auth/password-reset/request) for this email."
    )
    if dry_run:
        print("  [dry-run] would create the account here")
        return User(id="dry-run-owner-id", email=LEGACY_DATA_OWNER_EMAIL, display_name="Legacy Data")

    import secrets

    owner = User(
        email=LEGACY_DATA_OWNER_EMAIL,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        display_name="Legacy Data",
        email_verified=False,
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


def _migrate_watchlists(db, owner: User, dry_run: bool) -> tuple[int, int]:
    if not WATCHLISTS_DIR.exists():
        return 0, 0
    files = sorted(WATCHLISTS_DIR.glob("*.json"))
    for path in files:
        slug = path.stem
        try:
            tickers = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  SKIPPED watchlist '{slug}': could not read/parse ({exc})")
            continue
        print(f"  watchlist '{slug}': {len(tickers)} ticker(s)")
        if not dry_run:
            watchlist_store.save_tickers(db, owner.id, slug, tickers)
    imported = 0 if dry_run else db.query(WatchlistDB).filter_by(user_id=owner.id).count()
    return len(files), imported


def _migrate_paper_portfolios(db, owner: User, dry_run: bool) -> tuple[int, int]:
    if not PAPER_TRADING_DIR.exists():
        return 0, 0
    files = sorted(PAPER_TRADING_DIR.glob("*.json"))
    for path in files:
        slug = path.stem
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  SKIPPED portfolio '{slug}': could not read/parse ({exc})")
            continue
        print(
            f"  portfolio '{slug}': cash={state.get('cash')!r}, "
            f"{len(state.get('trades', []))} trade(s), {len(state.get('positions', {}))} open position(s)"
        )
        if not dry_run:
            paper_trading_store.save_portfolio(db, owner.id, slug, state)
    imported = 0 if dry_run else db.query(PaperPortfolioDB).filter_by(user_id=owner.id).count()
    return len(files), imported


def _migrate_experiments(db, owner: User, dry_run: bool) -> tuple[int, int]:
    if not EXPERIMENTS_DIR.exists():
        return 0, 0
    files = sorted(EXPERIMENTS_DIR.glob("*.json"))
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            experiment = _dict_to_experiment(data)
        except (json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
            print(f"  SKIPPED experiment '{path.stem}': could not read/parse ({exc})")
            continue
        print(f"  experiment '{experiment.id}': {experiment.name!r} (status={experiment.status}, fingerprint={experiment.fingerprint})")
        if not dry_run:
            experiments_store.save_experiment(db, owner.id, experiment)
    imported = 0 if dry_run else db.query(ExperimentDB).filter_by(user_id=owner.id).count()
    return len(files), imported


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report what would be migrated without writing anything.")
    args = parser.parse_args()

    print("=== JSON -> PostgreSQL legacy data migration ===")
    print(f"Mode: {'DRY RUN (no changes will be made)' if args.dry_run else 'LIVE'}")
    print()

    if not args.dry_run:
        backup_dir = _backup_json_directories()
        if backup_dir:
            print(f"Backed up existing JSON data to: {backup_dir.resolve()}")
        else:
            print("No existing JSON data found to back up.")
    print()

    db = SessionLocal()
    try:
        owner = _get_or_create_legacy_owner(db, args.dry_run)
        print()

        print("Watchlists:")
        wl_source, wl_imported = _migrate_watchlists(db, owner, args.dry_run)
        print("Paper-trading portfolios:")
        pt_source, pt_imported = _migrate_paper_portfolios(db, owner, args.dry_run)
        print("Experiments:")
        exp_source, exp_imported = _migrate_experiments(db, owner, args.dry_run)

        print()
        print("=== Verification ===")
        ok = True
        for label, source, imported in (
            ("Watchlists", wl_source, wl_imported),
            ("Paper-trading portfolios", pt_source, pt_imported),
            ("Experiments", exp_source, exp_imported),
        ):
            if args.dry_run:
                print(f"{label}: {source} source file(s) found (dry run - nothing imported)")
                continue
            status = "OK" if imported >= source else "MISMATCH"
            if status != "OK":
                ok = False
            print(f"{label}: {source} source file(s) -> {imported} row(s) now owned by the legacy account [{status}]")

        if not args.dry_run:
            print()
            if ok:
                print("All record counts verified. Migration complete.")
                print(f"To access this data, run the password-reset flow for: {LEGACY_DATA_OWNER_EMAIL}")
            else:
                print("WARNING: record count mismatch detected above - do not assume migration succeeded. Investigate before relying on this data.")
                return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
