# Deployment

**This documents how to deploy the application. It has not actually been
deployed anywhere by this codebase's own actions** - no infrastructure was
provisioned, no domain configured, no PostgreSQL server stood up. Treat
everything below as instructions to follow, not a description of a live
system.

## Recommended architecture

Nothing here is hardcoded into the app - it's provider-agnostic (a
`DATABASE_URL`, a `FRONTEND_URL`/`BACKEND_URL` pair, standard SMTP
settings). The choices below are a concrete, realistic starting point,
not a requirement.

| Concern | Recommendation | Cost | Why / caveat |
|---|---|---|---|
| Frontend hosting | **Vercel** | Free tier | Zero-config for Next.js (this app's exact framework); its free tier is a real, ongoing free tier, not a trial. |
| Backend hosting | **Render** (Web Service) | Free tier, with a real caveat | Free web services spin down after ~15 minutes of inactivity - the first request after idle pays a cold start (tens of seconds, since it's a full process restart, not just a DB wake-up). Acceptable for a low-traffic/personal deployment; upgrade to a paid instance to remove this if it matters. Fly.io is a reasonable alternative with a similar shape. |
| PostgreSQL | **Neon** | Free tier (see [DATABASE.md](DATABASE.md)) | Already justified above - genuinely free, not time-limited, `DATABASE_URL`-compatible with zero code changes. |
| Redis (only if `RATE_LIMIT_STORAGE_URL` is actually used) | **Upstash** | Free tier | Only needed once you run more than one backend instance/process - see [SECURITY.md](SECURITY.md#rate-limiting). Do not provision this for a single-instance deployment; there is nothing for it to do. |
| SMTP (transactional email) | **Resend** or **Brevo** | Free tier (low daily send limit - check current provider limits before relying on it at scale) | Either works with the existing `SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/`SMTP_PASSWORD` variables in `app/auth/email.py` unchanged - no provider-specific SDK needed. |
| DNS / domain | Whatever registrar you already use, pointed at Vercel (frontend) and Render (backend, typically a subdomain like `api.yourdomain.com`) | Domain registration cost only | Keep frontend and backend on the same registrable domain (different subdomains is fine) - see the CORS/cookies note below; a raw IP or an unrelated domain breaks session cookies. |
| HTTPS | Automatic on both Vercel and Render for custom domains | Free | `SESSION_COOKIE_SECURE` is forced on in production (see below), so this is not optional. |

This entire architecture fits inside free tiers for a low-traffic
deployment, with two honest, documented tradeoffs: Render's free-tier cold
start, and Neon's free-tier autosuspend cold start. Both only affect the
*first* request after a period of inactivity, not steady-state usage.

## Prerequisites

- A PostgreSQL server (see [DATABASE.md](DATABASE.md) - not verified
  against a real instance in this development environment, only against
  SQLite).
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
