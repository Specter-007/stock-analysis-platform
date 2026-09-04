# Legacy JSON → PostgreSQL migration

This document describes the one-time migration from the pre-multi-user
JSON-file stores (`backend/data/watchlists/`, `backend/data/paper_trading/`,
`backend/data/experiments/`) to the PostgreSQL-backed, user-owned schema
introduced by the production SaaS foundation.

## Why this exists

Before authentication existed, watchlists, paper-trading portfolios, and
experiments belonged to nobody in particular - they were just files on
disk. Every one of those records now needs a `user_id`. There is no way to
infer whose data it was, so this migration does **not guess**: it assigns
every pre-existing record to one explicitly-designated "legacy data owner"
account.

## The legacy data owner account

Controlled by the `LEGACY_DATA_OWNER_EMAIL` environment variable (see
`app/settings.py`, default `legacy-import@localhost`). The migration script:

1. Looks up a `User` with that email. If one already exists (e.g. from a
   previous run), it's reused - no duplicate account is ever created.
2. Otherwise creates one, with a **random, unusable password that is never
   printed, logged, or emailed anywhere.**

To actually sign into this account after migration, use the normal
password-reset flow:

```bash
curl -X POST http://localhost:8000/api/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "legacy-import@localhost"}'
```

With `EMAIL_PROVIDER=console` (the local-dev default), the reset link is
printed to the backend's log output rather than actually emailed - copy it
from there. In production, set `LEGACY_DATA_OWNER_EMAIL` to a real mailbox
you control *before* running the migration, and configure a real
`EMAIL_PROVIDER=smtp` so the reset link is actually delivered.

## Running it

Prerequisites: `DATABASE_URL` points at the target database, and
`alembic upgrade head` has already been run against it (see
[DATABASE.md](DATABASE.md)).

```bash
cd backend
python scripts/migrate_json_to_db.py --dry-run   # see what would happen, changes nothing
python scripts/migrate_json_to_db.py             # actually import
```

## What it guarantees

- **Backs up first.** Every JSON directory that has any files in it is
  copied to `backend/data/backups/pre_migration_<timestamp>/` before
  anything is written to the database. The original JSON files are never
  modified or deleted by this script, ever.
- **Idempotent.** Running it multiple times never creates duplicate rows -
  watchlists and paper portfolios are upserted by `(user, slug)`,
  experiments by their existing `id`. Re-running after a partial or
  interrupted run is safe.
- **Verified, not assumed.** After importing, it counts the source JSON
  files against the resulting database rows for the legacy owner and
  prints an explicit `OK` / `MISMATCH` per subsystem. A mismatch (e.g. one
  file failed to parse) makes the script exit with a non-zero status and a
  visible warning - it never reports success it didn't actually verify.
- **Preserves shape exactly.** Paper-trading state (cash, positions,
  trades, equity snapshots, benchmark basis) and experiment
  config/results/provenance/fingerprint/lifecycle status are stored
  byte-for-shape identical to the old JSON - only the storage backend
  changed, not the data model the quant/experiment logic reads.

## What it does not do

- It does not delete the source JSON files. Once you've verified the
  imported data in the app, removing the old `backend/data/{watchlists,
  paper_trading,experiments}/` directories is a manual decision for you to
  make, not something this script does automatically.
- It does not merge legacy data into an *existing* real user account. If
  you want a specific person (not the anonymous legacy-owner placeholder)
  to end up owning this data, that is a manual re-assignment (update the
  `user_id` column on the relevant rows) you perform after migration and
  after verifying the data is what you expect.
- It does not run Alembic migrations for you. Schema must already exist.

## Verifying the result

```sql
-- Counts per table, owned by the legacy account
SELECT count(*) FROM watchlists WHERE user_id = (SELECT id FROM users WHERE email = 'legacy-import@localhost');
SELECT count(*) FROM paper_portfolios WHERE user_id = (SELECT id FROM users WHERE email = 'legacy-import@localhost');
SELECT count(*) FROM experiments WHERE user_id = (SELECT id FROM users WHERE email = 'legacy-import@localhost');
```

Compare against the file counts in the pre-migration backup directory.
