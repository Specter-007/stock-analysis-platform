# Security

This document describes the security controls actually implemented in
this codebase. It is not a compliance certification - see the "Known
limitations" section at the end for what has *not* been done.

## Authentication & session security

See [AUTHENTICATION.md](AUTHENTICATION.md) for the full detail: Argon2id
password hashing, httpOnly `SameSite=Lax` session cookies (never a bearer
token in localStorage), server-side session revocation, single-use hashed
tokens for password reset/email verification/email change, and a generic
invalid-credentials error that never reveals whether an email is
registered.

## CSRF

Signed (itsdangerous) double-submit-cookie protection on every
state-changing (`POST`/`PATCH`/`DELETE`) authenticated endpoint -
`app.auth.dependencies.require_csrf`. Tested for all three outcomes
(missing header, wrong header value, correct header) in
`backend/tests/test_auth.py`.

## Authorization & IDOR prevention

**The frontend never enforces ownership - it is enforced on the server for
every request.** The pattern used throughout `app/watchlist`,
`app/paper_trading`, and `app/experiments`:

1. The authenticated user's id comes **only** from the verified session
   cookie (`app.auth.dependencies.get_current_user`) - never from a
   client-supplied field.
2. Every store/service function that reads or writes a user-owned row
   takes that `user_id` explicitly and includes it in the query
   (`WHERE user_id = :user_id AND slug = :slug`, or `WHERE user_id =
   :user_id AND id = :id`).
3. A lookup that doesn't match - because the resource doesn't exist *or*
   belongs to a different user - returns the same "not found" result
   either way (`app.auth.exceptions.ResourceNotFoundError` → HTTP 404).
   This is deliberate: it prevents an authenticated attacker from using a
   404-vs-403 response difference to enumerate other users' resource IDs.

**Critical security tests** (`backend/tests/test_idor.py`, 10 tests) prove
this over the real HTTP API with two independently-cookied clients sharing
one database - the actual attacker scenario:

- User B cannot see User A's watchlist tickers, and B's own delete/add
  actions never touch A's watchlist.
- User B cannot see User A's paper portfolio, and the "list my portfolios"
  endpoint never includes another user's portfolio.
- User B cannot GET, PATCH (notes), DELETE, or POST-run User A's
  experiment (each returns 404), and A's experiment is unaffected by B's
  attempts.
- All three subsystems reject a fully unauthenticated request (401).

The same pattern is applied to notifications (`test_notifications.py`) and
is exercised by the admin foundation's own tests (`test_admin.py` - a
non-admin gets the same 401 an unauthenticated caller would).

## CORS

`app.settings.CORS_ALLOWED_ORIGINS` is explicit (never `"*"`) and is
validated **at import time**: if `APP_ENV=production` and either no
origins are configured or `"*"` is one of them, the app raises and refuses
to start, rather than silently running with an insecure credentialed-CORS
configuration (a wildcard origin combined with `allow_credentials=True`
would let any website read a signed-in user's session via a cross-origin
fetch). Local dev defaults to `http://localhost:3000,http://127.0.0.1:3000`.
Real preflight (`OPTIONS`) requests are tested end-to-end in
`test_v5_cors.py` for every method the API actually uses - `TestClient`'s
in-process dispatch does not perform a real CORS preflight, so this had to
be tested against real HTTP behavior; doing so previously caught a real
bug (a missing `PATCH`/`DELETE` in `allow_methods` that had silently broken
the watchlist delete button in a real browser - see the V5 changelog in
the README).

## Rate limiting

`slowapi`, applied to:

- `/api/auth/register`, `/api/auth/login` - `RATE_LIMIT_AUTH` (default
  5/minute per IP)
- `/api/auth/password-reset/request` - `RATE_LIMIT_PASSWORD_RESET`
  (default 3/minute)
- `/api/support` (the contact form) - `RATE_LIMIT_CONTACT` (default
  3/minute)

**Documented limitation:** `slowapi`'s default storage is in-memory, so
limits are per-process. A multi-process/multi-instance production
deployment would need a shared store (e.g. Redis) for the limit to apply
globally - not added here per the "don't introduce infrastructure the app
doesn't otherwise need" instruction for this phase. Document this as a
gap, not a solved problem, when planning a multi-instance deployment.

Existing V4/V5 resource limits (max Monte Carlo simulations, max
sensitivity parameter combinations, max tickers per portfolio backtest,
max watchlist size) predate this phase and were audited, not rebuilt -
they remain in `app/config.py`.

## Security headers

`app.security_headers.SecurityHeadersMiddleware` sets, on every response
except `/docs`/`/redoc`/`/openapi.json` (which need a permissive CSP for
Swagger UI's own CDN-loaded assets - this is a pure JSON API otherwise, so
a strict CSP costs nothing real elsewhere):

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Frame-Options: DENY`
- `Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`
- `Strict-Transport-Security` (only when `APP_ENV=production`, since HSTS
  is only meaningful/safe over an actual HTTPS deployment)

## Input validation

Pydantic models validate every request body: email format, password
strength (min length + letter + digit), ticker format (existing
`normalize_and_validate_ticker`), timezone (checked against real IANA
`ZoneInfo` data, not just "any string"), category enums (contact form),
string length caps (subject ≤ 200 chars, message ≤ 5000 chars) to bound
payload size at the schema level.

## Database security

SQLAlchemy ORM / parameterized queries exclusively - no string-concatenated
SQL anywhere in this codebase. Foreign keys with explicit `ON DELETE`
behavior (`CASCADE` for owned data, `SET NULL` for support tickets).
Unique constraints on `(user_id, slug)` for watchlists/portfolios prevent
silent duplicate-slug collisions. The app connects with whatever
credentials `DATABASE_URL` specifies - **use a role with only the
privileges the application needs (not a superuser) in production; this is
an operational/deployment decision, not something the codebase itself can
enforce.**

## Secrets & environment configuration

- `SESSION_SECRET` (signs CSRF tokens) has an obviously-insecure
  documented default for local dev; `app.settings` raises at import time
  if `APP_ENV=production` and it's still at that default.
- `.env`, `.env.local`, and `backend/.env` are gitignored;
  `backend/.env.example` documents every variable with safe placeholder
  values, never real credentials.
- No secret is ever logged - passwords, session tokens, and reset/
  verification tokens are hashed before storage and never appear in log
  output; unhandled exceptions are logged server-side with
  `logger.exception` but returned to the client as a generic message
  (`app/api/errors.py`), never a raw stack trace.

## Dependency audit

`pip-audit` was run against `backend/requirements.txt` during the final
hardening pass:

```
Found 1 known vulnerability in 1 package
Name   Version ID              Fix Versions
------ ------- --------------- ------------
pytest 8.3.4   PYSEC-2026-1845 9.0.3
```

`pytest` is a test-time-only dependency - it is never imported by the
running application (`app.main`) and ships in no production artifact, so
this does not affect the deployed attack surface. Documented rather than
silently ignored; upgrading to pytest 9 (a major version) was not done in
this pass to avoid an unreviewed test-collection/fixture behavior change
this late in the hardening effort - track it as a follow-up.

This is an **automated dependency scan**, not a manual audit of each
package's source, and not a substitute for a human security review.

## Real PostgreSQL concurrency findings

`tests/test_postgresql_real.py` (see [DATABASE.md](DATABASE.md)) verified
two concrete concurrency properties against a real PostgreSQL server: a
second session correctly observes a first session's already-committed
write (no stale-read/lost-update), and a duplicate-slug race between two
sessions is rejected by the real unique constraint rather than silently
creating two rows or overwriting one. One deliberately **not** fixed in
this pass: paper-trading equity snapshots are appended to a JSON array
inside a single `paper_portfolios.state` column (see
[DATABASE.md](DATABASE.md)), not a separate table with its own unique
constraint - two genuinely concurrent requests for the *same* portfolio on
the *same* day (e.g. the same user with two browser tabs open) could in
principle both pass the "not already recorded today" check before either
commits, producing two snapshot entries for one day. This is a narrow,
low-severity window (a single user racing themselves, not a security
issue), not fixed here because doing so correctly would mean moving equity
snapshots to their own table - a genuine schema change beyond this
hardening pass's "do not rebuild the quant/persistence architecture"
scope. Documented as a known limitation, not silently accepted.

## Known limitations (honest, not exhaustive)

- No automated penetration test or third-party security audit has been
  performed - this document describes the controls implemented, not an
  independent verification of them.
- Rate limiting is per-process (see above) - not yet suitable for a
  horizontally-scaled multi-instance deployment without adding a shared
  store.
- No Web Application Firewall, DDoS protection, or intrusion detection is
  configured - these are typically reverse-proxy/CDN/hosting-provider
  concerns outside this application's own codebase.
- PostgreSQL itself (as opposed to the SQLAlchemy models targeting it) has
  not been verified in this development environment - see
  [DATABASE.md](DATABASE.md).
- This document has not been reviewed by a third-party security
  professional.
