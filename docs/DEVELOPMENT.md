# Development

## Prerequisites

- Python 3.12+ (backend)
- Node.js (frontend; see `frontend/package.json` for the Next.js/React
  versions actually pinned)
- No PostgreSQL install required for local development - the backend
  defaults to a local SQLite file (`backend/data/app.db`) when
  `DATABASE_URL` is unset. See [DATABASE.md](DATABASE.md).

## First-time setup

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
alembic upgrade head         # creates backend/data/app.db and its schema
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend defaults to calling the backend
at `http://localhost:8000` (`NEXT_PUBLIC_API_BASE_URL` in
`frontend/.env.local` if you need to override it).

## The cookie/CORS gotcha this phase actually hit

Session and CSRF cookies are `SameSite=Lax` (see
[AUTHENTICATION.md](AUTHENTICATION.md)), which are only sent on **same-site**
requests. During this phase's own end-to-end verification, a pre-existing
`frontend/.env.local` had:

```
NEXT_PUBLIC_API_BASE_URL=http://192.168.1.106:8000
```

...set for testing from another device on the LAN. Opening the frontend at
`http://localhost:3000` in a browser while it called the backend at a
*different host* (`192.168.1.106`) made every auth request genuinely
cross-site - the browser silently refused to store or send the session/CSRF
cookies at all, and login appeared to "do nothing." There was no bug in
the auth code; the frontend and backend simply weren't being accessed via
the same hostname.

**Rule of thumb:** whatever hostname is in your browser's address bar for
the frontend, `NEXT_PUBLIC_API_BASE_URL` should point at the backend via
that *same* hostname (just a different port is fine - `localhost:3000`
calling `localhost:8000` is same-site). If you need to test from another
device on your LAN, access the frontend via that machine's LAN IP too
(`http://192.168.1.x:3000`), not `localhost`.

## Running tests

```bash
cd backend
python -m pytest -q                              # everything, including real-network tests
python -m pytest -q -k "not integration_real_data"  # skip real Yahoo Finance calls (fast, deterministic)
```

`tests/test_integration_real_data.py` requires actual internet access and
is skipped automatically if Yahoo Finance isn't reachable. It registers (or
logs into, on a repeat run) a fixed test account against whatever database
`DATABASE_URL` points at - safe to run repeatedly against the local dev
SQLite database, since JSON stores/experiments it creates are cleaned up
in `finally` blocks.

Frontend checks:

```bash
cd frontend
npx tsc --noEmit
npx eslint .
npx next build
```

## Database resets during development

```bash
rm backend/data/app.db
cd backend && alembic upgrade head
```

If you have pre-existing JSON data (from before this phase, or from an
older single-user checkout) you want to bring into the fresh database, run
`python scripts/migrate_json_to_db.py` afterward - see
[MIGRATION.md](MIGRATION.md).

## Code layout

- `backend/app/{watchlist,paper_trading,experiments}/` - the three
  user-owned subsystems, each with a `store.py` (SQLAlchemy-backed,
  scoped by `user_id`) and `service.py` (business logic, unchanged from
  V4/V5 except for the added `user_id` scoping).
- `backend/app/auth/`, `backend/app/preferences/`, `backend/app/
  notifications/`, `backend/app/support/`, `backend/app/admin/` - the
  production SaaS foundation added in this phase.
- `backend/app/models_db/` - SQLAlchemy ORM models.
- `backend/app/db/` - engine/session setup, the naive-UTC timestamp
  convention, and the portable-JSON column type.
- `frontend/components/{auth,settings,onboarding,notifications,command-
  palette,legal,support}/` - the new SaaS-foundation UI, styled with the
  app's existing design tokens (`frontend/app/globals.css`) rather than a
  new component library.

## Style/architecture notes worth knowing before changing this code

- Every user-owned resource is looked up by `(user_id, slug-or-id)` at the
  store layer, never trusted from a client-supplied value alone - see
  [SECURITY.md](SECURITY.md#authorization--idor-prevention). If you add a
  new user-owned resource type, follow the same pattern and add an IDOR
  test to `tests/test_idor.py`.
- Timestamps are naive UTC everywhere in the database layer
  (`app.db.timeutil.utcnow_naive`) - never mix in a timezone-aware
  `datetime.now(timezone.utc)` when writing to a DB column, or you will
  hit the exact `TypeError` this project has hit multiple times before.
- The frontend's `useEffect`-based data fetching follows the pattern
  already established in `components/search/TickerSearch.tsx`: call the
  API function directly and handle the result in `.then()`/`.catch()`
  inside the effect (with a `cancelled` flag for cleanup), rather than
  defining a separate `async function` and calling it bare - the
  project's `eslint-plugin-react-hooks` `set-state-in-effect` rule flags
  the latter pattern.
