# Deployment

**This documents how to deploy the application.** Parts of it now describe
a real, live deployment; other parts are still instructions to follow, not
infrastructure that exists yet. The status line at the top of each
relevant section says which.

## Current deployment status

- **Frontend**: deployed to Vercel - **https://stock-analysis-platform-gamma.vercel.app**
- **Backend**: not yet deployed. `render.yaml` (repo root) and
  `backend/.python-version` are prepared and ready for a Render Blueprint
  deployment - see "Deploying the backend to Render" below for the exact
  steps and the current interim limitation (no database yet).
- **PostgreSQL / Redis / SMTP**: not yet provisioned. The backend, once
  deployed, will serve the public/stateless stock-analysis endpoints
  correctly without any of these - see the interim-limitation note below.
  Handled in a later phase.
- **Domain/DNS**: using the platforms' own generated URLs
  (`*.vercel.app` / `*.onrender.com`), no custom domain configured.

## Deploying the backend to Render

The repository root has a `render.yaml` Blueprint that defines the
backend as a free-tier Python web service (`rootDir: backend`, `pip
install -r requirements.txt`, `uvicorn app.main:app --host 0.0.0.0 --port
$PORT`, health check at `/api/health`). To deploy it:

1. In the Render dashboard: **New +** → **Blueprint** → connect the
   `Specter-007/stock-analysis-platform` GitHub repo → Render reads
   `render.yaml` and proposes the `stock-analyst-backend` service.
2. You will be prompted for the `sync: false` values `render.yaml`
   deliberately leaves blank (Render does not read secrets out of a repo
   file, and this one was written to never contain any):
   - `SESSION_SECRET` - generate a real one, e.g.
     `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
     Never reuse a value that has appeared anywhere in this repo or its
     history (none has - this generates a fresh one).
   - `DATABASE_URL` - **leave this blank for now**. See the limitation
     note immediately below for exactly what that means and doesn't mean.
   - `RATE_LIMIT_STORAGE_URL` - leave blank; not needed for a single
     instance.
3. `CORS_ALLOWED_ORIGINS` and `FRONTEND_URL` are already set in
   `render.yaml` to the real deployed Vercel URL above - update both if
   that URL ever changes (e.g. a custom domain is added later).
4. Deploy. Once Render assigns the service a URL
   (`https://stock-analyst-backend-XXXX.onrender.com` or similar), record
   it - the frontend needs it next (see "Frontend API URL" below).

**Interim limitation, stated plainly:** deploying with no `DATABASE_URL`
means this backend instance has no real database - it falls back to a
SQLite file *inside the Render container*, which is wiped on every
restart/redeploy. This is deliberately acceptable **only** because the
public stock-analysis endpoints (`/api/stock/*`, `/api/backtest/*`,
`/api/model`, `/api/compare`, etc. - see `app/api/routes_stock.py` and
siblings) never touch the database at all. **Do not use this deployment's
registration, login, watchlist, paper-trading, experiments, or settings
features** until a real `DATABASE_URL` (see [DATABASE.md](DATABASE.md)'s
Neon recommendation) is set and `alembic upgrade head` has been run
against it - anything saved before that point is not real, persistent
data. Running `python scripts/production_preflight.py` against this
configuration correctly reports `[FAIL] DATABASE_URL` - that is the
script working as intended, not a bug to silence.

## Frontend API URL - same-origin proxy (connecting Vercel to Render)

**Production does NOT call the Render backend directly from the browser.**
An earlier version of this document recommended pointing
`NEXT_PUBLIC_API_BASE_URL` straight at the Render URL - that architecture
has a real, confirmed bug: the frontend (`*.vercel.app`) and backend
(`*.onrender.com`) are different registrable domains, so a direct
cross-site call is genuinely cross-site, and the session/CSRF cookies
(`SameSite=Lax` - see `app/auth/cookies.py`) are **never attached** to a
cross-site `fetch`, regardless of `credentials: "include"`. Observed
symptom: `POST /api/auth/login` → `200`, immediately followed by
`GET /api/auth/me` → `401`, because the browser never sent the session
cookie back on the second request.

**Fix: a same-origin API proxy**, using Next.js's own `rewrites()`
(`frontend/next.config.ts`). The browser only ever talks to the frontend's
own origin (`/api/*`); Vercel forwards that server-side to the real
Render backend. From the browser's point of view every request - login,
`/me`, watchlist, everything - is same-origin, so `SameSite=Lax`,
`Secure`, and `HttpOnly` all keep working exactly as configured. **No
cookie or CORS security setting was loosened to fix this** - the backend's
`app/auth/cookies.py` is unchanged, and neither is its CORS/CSRF
configuration.

Required Vercel environment variables for this to work:

| Variable | Value | Scope |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | **empty string** (literally blank - not unset, not `http://localhost:8000`) | Production |
| `BACKEND_URL` | the real Render URL, e.g. `https://stock-analyst-backend.onrender.com` (no trailing slash) | Production (server-only - never exposed to the browser, deliberately not `NEXT_PUBLIC_*`) |

Setting `NEXT_PUBLIC_API_BASE_URL` to an empty string (not leaving it
unset) matters: `frontend/lib/api.ts` uses `??`, not `||`, specifically so
an intentional empty string is respected as "same-origin" rather than
being treated as falsy and silently falling back to `localhost:8000` -
see the regression tests in `frontend/lib/api.test.ts`.

Steps:

1. Vercel dashboard → **Settings** → **Environment Variables** → add both
   variables above, scoped to Production.
2. **Trigger a new deployment** - Next.js bakes `NEXT_PUBLIC_*` variables
   into the build at build time; `BACKEND_URL` is read at request time by
   Vercel's rewrite layer, but redeploying after any env var change is the
   safe default regardless (**Deployments** → **⋯** → **Redeploy**, or
   push a new commit).
3. Local development is unaffected: `frontend/.env.local` (gitignored)
   keeps `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` set, so
   `npm run dev` continues to call a locally-running backend directly -
   `localhost:3000` and `localhost:8000` differ only by port, which is
   same-site for cookie purposes, so the proxy was never needed there.
   Verified locally end-to-end (production build + `next start`, a real
   local backend, and the proxy wired via `BACKEND_URL`) before this was
   documented: register, login, `/me`, logout, CSRF-protected requests,
   watchlist, preferences, and paper trading all round-tripped correctly
   through `/api/*` on the frontend's own origin.

## Recommended architecture

Nothing here is hardcoded into the app - it's provider-agnostic (a
`DATABASE_URL`, a `FRONTEND_URL`/`BACKEND_URL` pair, standard SMTP
settings). The choices below are a concrete, realistic starting point,
not a requirement.

| Concern | Recommendation | Free-tier limits (verified current as of this phase, Sept 2026) | Caveat |
|---|---|---|---|
| Frontend hosting | **Vercel** (Hobby) | 100 GB data transfer/mo, 1M edge requests, 1M function invocations, 4 CPU-hours, 10s function timeout - no overage billing, project pauses if exceeded. | Zero-config for Next.js. **Hobby is restricted to personal, non-commercial use** - fine for this app as-is, but monetizing it later requires upgrading to Pro. |
| Backend hosting | **Render** (Web Service, free) | 750 free instance-hours/month **per workspace** (shared across every free service in the account, not per-service), 512 MB RAM / 0.1 CPU. | Spins down after 15 min idle; cold start is **30-60s** (a real process restart, not just a DB wake-up). Do not use Render's own free Postgres (expires after 30 days) - use Neon instead, as recommended below. Fly.io is a reasonable alternative with a similar shape. |
| PostgreSQL | **Neon** | 100 CU-hours/month, 0.5 GB storage, up to 100 projects, autosuspend after **5 min** idle. Not time-limited (unlike Render's). | Already justified above - genuinely free indefinitely, `DATABASE_URL`-compatible with zero code changes. Compute/storage pricing dropped substantially after Neon's 2025 Databricks acquisition, for whenever the free tier is outgrown. |
| Redis (only if `RATE_LIMIT_STORAGE_URL` is actually used) | **Upstash** | 256 MB storage, 500,000 commands/month, 10 GB bandwidth/month - **permanent**, does not expire. | Only needed once you run more than one backend instance/process - see [SECURITY.md](SECURITY.md#rate-limiting). Do not provision this for a single-instance deployment; there is nothing for it to do. |
| SMTP (transactional email) | **Resend** | 3,000 emails/month, capped at **100/day**, one verified sending domain. | Works with the existing `SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/`SMTP_PASSWORD` variables in `app/auth/email.py` unchanged - no provider-specific SDK needed. The 100/day cap is a real constraint if verification/reset email volume ever grows past personal-scale use. Brevo (300/day free) is a reasonable alternative if that cap is reached. |
| DNS / domain | Whatever registrar you already use, pointed at Vercel (frontend) and Render (backend, typically a subdomain like `api.yourdomain.com`) | Domain registration cost only | Keep frontend and backend on the same registrable domain (different subdomains is fine) - see the CORS/cookies note below; a raw IP or an unrelated domain breaks session cookies. |
| HTTPS | Automatic on both Vercel and Render for custom domains | Free | `SESSION_COOKIE_SECURE` is forced on in production (see below), so this is not optional. |

This entire architecture fits inside free tiers for a low-traffic
deployment, with three honest, documented tradeoffs: Render's free-tier
cold start (30-60s), Neon's free-tier autosuspend cold start (5 min idle
threshold), and Resend's 100-email/day cap. All three only affect
first-request-after-idle latency or high-volume sending, not steady-state
low-traffic usage - re-verify these numbers against each provider's own
current pricing page before relying on them, since free-tier terms change
without notice.

## Prerequisites

- A PostgreSQL server (see [DATABASE.md](DATABASE.md) - schema,
  constraints, and concurrency behavior verified against a real disposable
  PostgreSQL server in this development environment; a real *managed*
  provider instance has not been, and may differ in configuration
  defaults - re-run `alembic upgrade head` and the test suite against your
  actual target before relying on it).
- A place to run the backend (any host that can run Python 3.12+ and
  `uvicorn`/`gunicorn`) and the frontend (any host that can run
  `next start`, or a static/edge platform that supports Next.js's
  server-rendered routes - this app uses dynamic routes and cookies, so a
  purely static export will not work).
- A real SMTP provider if you want verification/reset emails actually
  delivered (`EMAIL_PROVIDER=smtp`) - without one, the app runs correctly
  but honestly reports that no email was sent (see
  [AUTHENTICATION.md](AUTHENTICATION.md)).

## Required environment variables (backend)

See `backend/.env.example` for the full list with placeholder values.
The ones that matter most for a production launch:

| Variable | Production requirement |
|---|---|
| `APP_ENV` | Must be `production` - this flips several other checks below from "warn" to "refuse to start." |
| `DATABASE_URL` | A real PostgreSQL connection string. |
| `SESSION_SECRET` | A real, private, random secret - the app refuses to start with the dev placeholder when `APP_ENV=production`. |
| `CORS_ALLOWED_ORIGINS` | Your real frontend origin(s), comma-separated. Never `*`. The app refuses to start with `*` or an empty value when `APP_ENV=production`. |
| `SESSION_COOKIE_SECURE` | Forced on automatically in production; only relevant to override for local HTTPS testing. |
| `FRONTEND_URL` / `BACKEND_URL` | Used to build links in emails (password reset, verification). |
| `EMAIL_PROVIDER` | `smtp` plus `SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/`SMTP_PASSWORD` if you want real email delivery; otherwise stays `console` and the app is honest about not having sent anything. |
| `RATE_LIMIT_STORAGE_URL` | Optional. Only needed if you run more than one backend process/instance - set to a `redis://` URL to share rate-limit state across them. Unset means per-process in-memory limiting (correct for one instance). Falls back to per-process limiting automatically if the configured Redis is unreachable. |
| `LEGACY_DATA_OWNER_EMAIL` | Only relevant if you run the JSON→Postgres migration (see [MIGRATION.md](MIGRATION.md)). |

## Start commands

```bash
# Backend (from backend/)
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
# or, behind a process manager: gunicorn -k uvicorn.workers.UvicornWorker app.main:app

# Frontend (from frontend/)
npm run build
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com npm run start
```

`NEXT_PUBLIC_API_BASE_URL` is baked in at build time for a production
Next.js build - set it correctly *before* `npm run build`, not after.

## Preflight check

Before starting the backend in a real deployment, run:

```bash
cd backend
python scripts/production_preflight.py
```

It validates `APP_ENV`, `SESSION_SECRET`, `CORS_ALLOWED_ORIGINS`, `DATABASE_URL` (including actually
connecting to it and checking that `alembic upgrade head` has actually been run against it - a
reachable-but-unmigrated database is a `[FAIL]`, not a `[PASS]`), `EMAIL_PROVIDER`/SMTP completeness,
`RATE_LIMIT_STORAGE_URL` reachability (a `[WARN]` if unreachable, never a `[FAIL]` - the app already
falls back to per-process limiting), and `SESSION_COOKIE_SECURE` - printing `[PASS]`/`[WARN]`/`[FAIL]`
lines and exiting non-zero on a fundamentally broken configuration. It never prints a secret's actual
value. This is a manual step - it is not run automatically by the application itself.

## Database migration on deploy

Run `alembic upgrade head` as a release step, before the new backend code
starts serving traffic. Never apply a migration by hand-editing the
production schema.

## Health / readiness

- `GET /api/health` - liveness, no dependency checks, always fast. Use for
  a basic "is the process alive" check.
- `GET /api/health/ready` - additionally runs a real `SELECT 1` against
  the database. Use this as the orchestrator's readiness probe so traffic
  isn't routed to an instance that can't reach its database.

Neither endpoint calls Yahoo Finance - an external market-data outage
should never make this service report itself as unhealthy.

## CORS / cookies across domains

Session and CSRF cookies are `SameSite=Lax`. This works correctly when the
frontend and backend share the same **registrable domain** (e.g.
`app.example.com` calling `api.example.com` - same site, different
subdomain - is fine) but **will not work** if the frontend calls the
backend via a raw IP address or an entirely different domain than the one
the browser has open, because that is a genuinely cross-site request and
`SameSite=Lax` cookies are not sent on cross-site `fetch`/XHR. This was
discovered and fixed during this phase's own local verification (a
pre-existing `.env.local` pointed the frontend at the backend's LAN IP
while the browser had the page open via `localhost`, which silently
dropped every cookie) - see [DEVELOPMENT.md](DEVELOPMENT.md). Plan your
production domain names with this constraint in mind.

**This applied directly to, and was confirmed as a real bug in, the
Vercel + Render deployment**: `stock-analysis-platform-gamma.vercel.app`
and `*.onrender.com` are different registrable domains, so a direct
browser-to-backend call is genuinely cross-site, and session/CSRF cookies
were never sent back on the follow-up request (login succeeded, `/me`
returned 401). **Resolved** via the same-origin API proxy described above
("Frontend API URL - same-origin proxy") rather than by loosening
`SameSite` or CSRF - the browser now only ever talks to its own origin,
so this constraint no longer applies to the deployed app as configured. A
shared custom domain (`app.yourdomain.com` + `api.yourdomain.com`) remains
a reasonable alternative if the proxy hop's extra latency ever matters,
but is not required for correct or secure behavior.

## Reverse proxy / HTTPS

Terminate TLS at a reverse proxy (nginx, Caddy, your cloud provider's load
balancer) in front of `uvicorn`/`gunicorn`. `SESSION_COOKIE_SECURE` is
forced on in production, so the cookie will not be set at all over plain
HTTP - the app must actually be served over HTTPS end-to-end (or with the
proxy terminating TLS and forwarding to the app over a trusted internal
network) for login to work in production.

## Static assets

Next.js serves its own static assets (`_next/static/...`) - no separate
CDN configuration is required to function, though putting a CDN in front
of them is a reasonable production optimization outside this app's scope.

## Logging

`app/utils/logging_config.py` configures structured logging. Auth
failures, rate-limit rejections, and unhandled exceptions are logged
server-side (`logger.warning`/`logger.exception`) without ever including
passwords, tokens, or API keys - only the generic error is returned to the
client. Point your log aggregator at stdout/stderr; no file-based logging
is configured.

Every request is assigned a correlation id (`app/request_id.py`), returned
as an `X-Request-ID` response header and included in every log line for
that request (`[request_id]` in the log format) - grep a user-reported
`X-Request-ID` straight to the relevant server logs. A caller-supplied id
(e.g. from an upstream proxy/CDN) is reused if it looks like a reasonable
token, otherwise a fresh one is generated rather than trusting it verbatim
into logs.

## Backups

See [DATABASE.md](DATABASE.md#backups-and-recovery) - **no automated
backup system is configured by this codebase.** Set one up with your
PostgreSQL host/provider before relying on this in production.

## Not tied to one hosting provider

Nothing here assumes a specific cloud (no provider-specific SDK calls, no
proprietary managed-service dependencies beyond "a PostgreSQL database"
and "somewhere to run a Python process and a Node process"). Deploy to
whatever you already use - a VM, a container platform, a PaaS that
supports both processes, etc.

## Full deployment procedure (first launch)

A concrete, ordered checklist for taking this app from "code in a repo" to
"actually serving real traffic," using the architecture recommended above
(substitute your own providers - the steps are the same shape). **Do not
mark a step done because the *code* supports it - each one below means
you have actually performed the action against a real external service.**

1. **Create production services** - a Neon (or other) PostgreSQL project,
   a Render (or other) Web Service for the backend, a Vercel project for
   the frontend, and - only if you intend to run more than one backend
   instance/process - an Upstash (or other) Redis instance.
2. **Configure environment variables** - set every variable in
   `backend/.env.example` on the backend host's real environment-variable
   settings (never committed to the repo): `APP_ENV=production`,
   `SESSION_SECRET` (a real random value), `CORS_ALLOWED_ORIGINS` (your
   real frontend origin), `FRONTEND_URL`/`BACKEND_URL`, and set
   `NEXT_PUBLIC_API_BASE_URL`/`NEXT_PUBLIC_SITE_URL` on the frontend host.
3. **Configure PostgreSQL** - copy the provider's connection string
   (already includes `sslmode=require` or equivalent) into `DATABASE_URL`
   on the backend host. Do not hand-edit it into a different shape.
4. **Run migrations** - `alembic upgrade head` against that `DATABASE_URL`
   as a release step, before the new backend code starts serving traffic
   (see "Database migration on deploy" above).
5. **Configure SMTP** - set `EMAIL_PROVIDER=smtp` plus `SMTP_HOST`/
   `SMTP_PORT`/`SMTP_USERNAME`/`SMTP_PASSWORD`/`EMAIL_FROM_ADDRESS` from
   your transactional email provider (Resend/Brevo/etc.).
6. **Configure Redis (only if applicable)** - if you provisioned one in
   step 1, set `RATE_LIMIT_STORAGE_URL` to its connection string. Skip
   this step entirely for a single-instance deployment - there is nothing
   for it to do, and the app runs correctly without it.
7. **Configure backups** - enable your PostgreSQL provider's point-in-time
   recovery/automated backup feature in its dashboard (see
   [DATABASE.md](DATABASE.md#backups-and-recovery)). This is a real,
   provider-side action - the codebase cannot do it for you.
8. **Configure domain/DNS** - point your domain's DNS at Vercel (frontend)
   and your backend host (typically a subdomain such as
   `api.yourdomain.com`), keeping both on the same registrable domain (see
   the CORS/cookies note above).
9. **Enable HTTPS** - typically automatic once DNS is configured on
   Vercel/Render-style platforms; confirm the certificate is actually
   issued and serving before continuing.
10. **Deploy the backend** - push/trigger a deploy of `backend/` to the
    host configured in step 1, with `uvicorn`/`gunicorn` as the start
    command (see "Start commands" above).
11. **Deploy the frontend** - push/trigger a deploy of `frontend/` to
    Vercel, with `NEXT_PUBLIC_API_BASE_URL` already set correctly (it is
    baked in at build time, not read at runtime).
12. **Verify health endpoints** - `curl https://api.yourdomain.com/api/health`
    and `.../api/health/ready` both return `200` with the expected JSON
    body (see "Health / readiness" above).
13. **Run smoke tests** - manually load the frontend's home page, the
    login page, and one public tool page (e.g. `/analysis?ticker=AAPL`)
    in a real browser against the real deployed URLs, confirming no
    console errors and no failed network requests.
14. **Verify authentication** - register a real test account through the
    deployed frontend, confirm the session cookie is set (check dev tools
    - `Secure`, `HttpOnly`, `SameSite=Lax`), sign out, sign back in.
15. **Verify email verification** - confirm the verification email is
    actually delivered to a real inbox (not just logged), and that
    clicking its link verifies the account.
16. **Verify password reset** - request a reset for the test account,
    confirm the email arrives, and that the reset link actually changes
    the password and invalidates the old one.
17. **Verify database operations** - create a watchlist entry, a paper
    trade, and an experiment through the real deployed UI; confirm each
    persists across a page reload (i.e. is actually round-tripping through
    the real production database, not a stale client cache).
18. **Verify rate limiting** - deliberately trigger it (e.g. several rapid
    failed login attempts) and confirm a `429` response appears, using
    whatever storage backend you actually configured in step 6.
19. **Verify user isolation** - register a second real test account and
    confirm it cannot see the first account's watchlist/portfolio/
    experiments (the same property `backend/tests/test_idor.py` proves
    locally - this step re-confirms it against the real deployed system).
20. **Verify export, deletion, and rollback** - use the first test
    account's Settings → Privacy → "Export my data" and confirm the
    download contains real data; delete the second test account and
    confirm its data is gone; and confirm you know the rollback procedure
    for a bad deploy (`alembic downgrade -1` for a bad migration, your
    host's previous-deploy/rollback feature for a bad code deploy) *before*
    you need it under pressure, not after.

**Do not consider a step complete if it depends on an external service you
have not actually configured** - a documented environment variable with no
real account behind it is not the same as a working integration.
