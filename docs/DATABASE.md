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

## Choosing a managed PostgreSQL provider

The app has no provider-specific code - anything that speaks
`postgresql+psycopg2://` over `DATABASE_URL` works unchanged. Evaluated for
this pass, with an eye toward "prefer simple/low-cost, never at the
expense of correctness":

| Provider | Free tier | Notable tradeoff |
|---|---|---|
| **Neon** (recommended) | Yes, genuinely free and not time-limited (storage-capped, not calendar-capped). | Autosuspends after inactivity - the first query after idle pays a cold-start (typically 1-3s) to resume the compute. Ships a separate pooled connection string (PgBouncer, transaction mode) alongside the direct one. |
| **Supabase** | Yes, free tier available. | Free-tier projects pause after a period of inactivity and require a manual dashboard action to resume - worse for an app that might sit unused between sessions than Neon's automatic resume. Bundles auth/storage/realtime features this app doesn't use. |
| **Render (managed Postgres)** | Time-limited only - free Postgres instances are **deleted after 90 days**, not indefinitely free. | Not a realistic "free tier" for anything beyond a demo; would require the paid tier for a real deployment. |
| **Railway** | No meaningful free tier (usage-based billing from the start). | Good developer experience, but a paid requirement, not a free option. |

**Recommendation: Neon.** It's the only option here that's both genuinely
free indefinitely and requires zero code changes - copy its pooled
connection string (already includes `?sslmode=require`) into
`DATABASE_URL`, run `alembic upgrade head`, done. The autosuspend
cold-start is a real, honest limitation for a low-traffic deployment (the
first request after a period of idle will be slower) - acceptable for a
personal/small-scale deployment, and removable by upgrading to Neon's
always-on tier if that latency becomes a problem. Supabase is a fine
second choice if you already use it for something else; Render/Railway
are not free in any way that holds up for a real, ongoing deployment.

**SSL/TLS:** not configured in application code - it's carried entirely in
the `DATABASE_URL` query string (e.g. `?sslmode=require`). Every managed
provider's own connection-string generator already includes this; use the
string they give you verbatim rather than constructing one by hand.

**Connection pooling:** `app/db/base.py` sets `pool_pre_ping=True` (so a
connection the provider silently closed server-side is detected and
transparently replaced instead of surfacing as a 500 on the next request)
and `pool_recycle=1800` (proactively replaces pooled connections older
than 30 minutes, for providers that enforce a hard connection lifetime).
SQLAlchemy's own pool defaults otherwise apply (`pool_size=5,
max_overflow=10` - up to 15 connections per backend **process**). If you
run multiple worker processes (`uvicorn --workers N`) against a
connection-limited free tier, either lower these via
`create_engine(..., pool_size=..., max_overflow=...)` or use the
provider's own pooled connection string (Neon/Supabase both offer a
PgBouncer-fronted variant intended for exactly this).

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

**No backup system has been configured or automated by this repository.**
This section documents the real strategy to use for the recommended
Neon deployment (see above), and the manual fallback mechanics - not a
claim that backups are already running. Never treat this document as
"backups are handled" until you have actually enabled and verified one of
the options below against your own project.

**Recommended: enable the provider's built-in backups.** Neon retains
point-in-time recovery history automatically (retention window depends on
plan - check your current plan's retention period in the Neon dashboard,
since free-tier retention is shorter than paid tiers) and lets you restore
to any point within that window, or branch a new database from a past
point, from the dashboard - no application code or cron job required.
Supabase offers the equivalent under its own dashboard's backup settings.
**This still requires a one-time action on your part** (confirming the
retention window meets your needs, and - for providers where it isn't
automatic - actually turning it on); this repository cannot do that for
you from inside the codebase.

- **Frequency/retention:** governed by the provider's plan, not by this
  app. Record whatever your actual plan's retention window is (e.g. "7
  days of point-in-time recovery on Neon's free tier" - verify the current
  number for your plan rather than trusting this document to stay
  accurate) somewhere your team will see it before assuming a longer
  window is available.
- **Verification:** periodically perform an actual test restore (to a
  throwaway branch/database, not production) and confirm the app starts
  and reads real data against it - a backup that has never been restored
  is unverified, not a backup.
- **Manual dump (works against any Postgres, provider-native backups or
  not):** `pg_dump -Fc "$DATABASE_URL" > backup.dump`
- **Restore:** `pg_restore -d "$DATABASE_URL" backup.dump`
- **Point-in-time recovery via WAL archiving** is what the provider-native
  option above already gives you; only relevant to configure by hand
  (`archive_mode` + a WAL-shipping destination) for a fully self-hosted
  Postgres server, which is not what this app's recommended architecture
  uses.
- **Migration rollback:** `alembic downgrade -1` reverts the schema; it
  does **not** restore data a destructive migration may have dropped -
  always take a real backup (a manual `pg_dump`, or confirm your
  provider's PITR window covers the change) before running a migration
  that drops or alters a column in a production environment with real
  data.
- **Disaster recovery expectation:** if the database is lost entirely
  (accidental deletion, provider incident), recovery time is bounded by
  how recently you verified a restore actually works, not by how recently
  a backup was *taken* - an untested backup is a guess, not a plan.

## Local dev workflow

```bash
cd backend
python -m venv venv && venv/Scripts/activate  # or source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head        # creates backend/data/app.db (SQLite)
python scripts/migrate_json_to_db.py  # optional: import pre-existing JSON data
uvicorn app.main:app --reload
```
