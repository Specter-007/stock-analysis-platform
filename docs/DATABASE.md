# Database

## Target architecture

Production target is **PostgreSQL**, accessed through **SQLAlchemy 2.x** ORM
models and versioned with **Alembic** migrations. This is a new addition on
top of the existing V1-V5 quant platform, which had no database before this
phase - watchlists, paper-trading portfolios, and experiments were plain
JSON files on disk (see [MIGRATION.md](MIGRATION.md) for how that data was
imported).

**Honesty note - updated after real PostgreSQL validation:** this
development environment has no system-installed PostgreSQL server and no
Docker either. Real PostgreSQL validation was still performed - not
skipped - using [`pgserver`](https://pypi.org/project/pgserver/), a
pip-installable package bundling a genuine, disposable PostgreSQL 16.2
server binary (no system install, no admin rights, no Docker required;
see `backend/requirements-dev.txt` and
`backend/tests/test_postgresql_real.py`, 16 tests). Verified for real: a
fresh `alembic upgrade head` from an empty database, `downgrade base` then
re-`upgrade head`, every table/JSONB-column/foreign-key/unique-constraint
matching the intended schema, cascade deletes (both raw ORM and through
the actual `app.auth.service` code), transaction rollback, the naive-UTC
timestamp convention *not* silently becoming timezone-aware, multi-user
ownership isolation through the real service layer, and two concurrency
scenarios (a second session seeing a first session's committed write, and
a duplicate-slug race being rejected by the unique constraint rather than
silently lost). Two real Windows-specific bugs were found and fixed while
building this validation - see that test file's module docstring.
**Still not verified:** a real managed PostgreSQL provider (RDS, Cloud
SQL, Supabase, etc.) or a Docker-based Postgres, which may differ in
configuration defaults from this embedded build - re-run `alembic upgrade
head` plus the application's test suite against your actual production
target before launch.

## Connection configuration

Everything is driven by the `DATABASE_URL` environment variable
(`backend/app/db/base.py`):

```
# Production
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/stock_analyst

# Local dev/test default if DATABASE_URL is unset
sqlite:///./data/app.db
```

The exact same ORM models and Alembic migrations run against either
backend. The one place the two dialects genuinely differ - JSON columns -
uses `sqlalchemy.JSON().with_variant(JSONB, "postgresql")`
(`app/db/types.py`): native, indexable `JSONB` on PostgreSQL, a portable
`JSON` (TEXT-backed) column on SQLite.

Every timestamp column is stored as **naive UTC** (`app/db/timeutil.py`),
never timezone-aware. This is a deliberate project-wide convention, not an
oversight: SQLite does not preserve `tzinfo` across a round-trip (a
`DateTime(timezone=True)` column reads back as naive), so comparing a
freshly loaded row's timestamp against `datetime.now(timezone.utc)` raises
`TypeError: can't compare offset-naive and offset-aware datetimes` - this
project has hit exactly this bug class multiple times before in the quant
engine itself, so the schema commits to one convention (naive UTC
everywhere) that behaves identically on SQLite and PostgreSQL instead of
special-casing per dialect.

## Schema

Defined in `backend/app/models_db/`, one module per entity:

| Table | Purpose |
|---|---|
| `users` | Account: email, Argon2id password hash, display name, role, verification/active flags, timestamps. |
| `user_preferences` | 1:1 with `users`: timezone, default benchmark, theme, notification toggles, marketing consent, terms/privacy acceptance timestamps, onboarding state. |
| `user_sessions` | Login sessions: only the SHA-256 hash of the session token is stored, plus expiry/revocation/user-agent/IP. |
| `auth_tokens` | Single-use tokens for password reset / email verification / email change - only the hash is stored. |
| `notifications` | Real-event notifications, per user. |
| `support_requests` | Contact-form submissions; `user_id` nullable (anonymous senders allowed), `ON DELETE SET NULL`. |
| `watchlists` | User-owned, unique on `(user_id, slug)`. `tickers` is a JSON array. |
| `paper_portfolios` | User-owned, unique on `(user_id, slug)`. `state` is the entire existing paper-trading state dict (cash, positions, trades, equity snapshots, benchmark basis) - unchanged shape from the old JSON-file format. |
| `experiments` | User-owned. `config`/`results`/`data_provenance` are JSON columns holding the same structures the V5 Experiment Lab already used; `created_at`/`updated_at` are ISO-8601 strings (the service layer, not the DB, owns these timestamps). |

All user-owned tables have `user_id` with `ON DELETE CASCADE` back to
`users` - deleting an account removes every row it owns in one transaction
via the foreign keys, not application-level cleanup code.

## Migrations (Alembic)

```bash
cd backend

# Apply all migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Generate a new migration after changing a model
alembic revision --autogenerate -m "describe the change"
```

`alembic/env.py` reads the same `DATABASE_URL` the app itself uses (never a
hardcoded URL in `alembic.ini`), so `alembic upgrade head` always targets
whatever database the app is currently configured for.

**Known autogenerate quirk:** a migration touching a `JSON().with_variant
(JSONB, ...)` column sometimes omits the `from sqlalchemy import Text`
import that the rendered `postgresql.JSONB(astext_type=Text())` expression
needs. If a freshly generated migration fails with `NameError: name 'Text'
is not defined`, add that import manually at the top of the generated file
- this has already been fixed once in the initial migration and is
documented here so it isn't a surprise next time.

**Never** edit a production schema by hand outside of a migration.

## Backups and recovery

**No backup system has been configured or automated in this repository.**
This section documents the mechanics you would use, not a claim that
backups are already running - do not treat this as "backups are handled."

- **Manual dump:** `pg_dump -Fc stock_analyst > backup.dump`
- **Restore:** `pg_restore -d stock_analyst backup.dump`
- **Point-in-time recovery** requires WAL archiving, which is a PostgreSQL
  server/hosting-provider configuration decision outside this repo's
  scope - most managed Postgres providers (RDS, Cloud SQL, Supabase, etc.)
  offer this as a checkbox; a self-hosted server needs `archive_mode` and
  a WAL-shipping destination configured explicitly.
- **Migration rollback:** `alembic downgrade -1` reverts the schema; it
  does **not** restore data a destructive migration may have dropped -
  always take a real database backup before running a migration that
  drops or alters a column in a production environment with real data.

## Local dev workflow

```bash
cd backend
python -m venv venv && venv/Scripts/activate  # or source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head        # creates backend/data/app.db (SQLite)
python scripts/migrate_json_to_db.py  # optional: import pre-existing JSON data
uvicorn app.main:app --reload
```
