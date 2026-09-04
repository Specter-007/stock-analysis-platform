# Authentication

## Summary

Cookie-based sessions (not JWTs/localStorage tokens), Argon2id password
hashing, server-tracked revocable sessions, double-submit-cookie CSRF
protection, and single-use expiring tokens for password reset/email
verification/email change. All of it lives under `backend/app/auth/`.

## Password storage

Argon2id via `argon2-cffi` (`argon2.PasswordHasher`, whose default `type`
is Argon2id) - the OWASP-recommended default for new applications. Never a
manually implemented hash (bare SHA-256/MD5). On a successful login, if the
stored hash was made with weaker-than-current parameters (e.g. after an
argon2-cffi default upgrade), it is opportunistically re-hashed - this is
never treated as a security failure, only a chance to keep hashes current.

## Sessions

- On login/register, a high-entropy random token (`secrets.token_urlsafe
  (32)`) is generated. Only its **SHA-256 hash** is stored in the
  `user_sessions` table - a database read alone can never be replayed as a
  live credential, mirroring how the password itself is stored.
- The raw token is set as an **httpOnly**, `SameSite=Lax` cookie
  (`session_token`) - never readable by JavaScript, which defends against
  session theft via XSS. `Secure` is forced on automatically when
  `APP_ENV=production`.
- Sessions expire after `SESSION_TTL_DAYS` (default 30) and can be revoked
  individually or in bulk ("sign out of all other sessions") from
  Settings → Security, which lists every active session's user-agent and
  last-seen time.
- Changing your password revokes every other session automatically.
  Resetting your password via the forgot-password flow revokes **every**
  session, including the current one.

### Why cookies, not a bearer token in localStorage

httpOnly cookies are the harder target for XSS-based token theft (the
token is never reachable from page JavaScript at all). The tradeoff is
CSRF exposure, which is why CSRF protection (below) exists specifically
*because* this project chose cookies.

## CSRF protection

Double-submit cookie pattern, signed with `itsdangerous`:

1. On login/register, a second cookie (`csrf_token`) is set - **not**
   httpOnly, so the frontend's own JavaScript can read it - containing an
   `itsdangerous`-signed token bound to the session id.
2. Every state-changing request (`POST`/`PATCH`/`DELETE`) must echo that
   exact cookie value back in an `X-CSRF-Token` header
   (`frontend/lib/api.ts` does this automatically for every non-GET
   request).
3. The backend (`app.auth.dependencies.require_csrf`) checks that the
   header value matches the cookie **and** verifies the signature resolves
   to the current session - a cross-origin attacker can trigger a
   cookie-carrying request but cannot read the cookie's value to put it in
   the header, so the check fails.

## Registration

Requires `email`, `password` (min 8 chars, at least one letter and one
digit), `display_name`, and **`accept_terms: true`** (a request without it,
or with it `false`, is rejected with a 422 - there is no default that
silently accepts on the user's behalf). `marketing_consent` is a separate,
independently opted-in boolean defaulting to `false` - accepting the Terms
of Service never implies marketing consent.

A verification email is triggered automatically at registration (see
[Email](#email) below for what "sent" actually means in this environment).

## Login

Always returns the **identical generic message** ("Incorrect email or
password") whether the email is unknown, the password is wrong, or the
account is inactive - verified by an automated test
(`test_login_wrong_password_and_unknown_email_return_identical_generic_error`).
When the email is unknown, a dummy Argon2 verification still runs so the
response time doesn't leak which case occurred via a timing side-channel.
Rate-limited (`RATE_LIMIT_AUTH`, default 5/minute per IP).

## Password reset

`POST /api/auth/password-reset/request` **always** returns the same
message regardless of whether the email is registered - it never confirms
or denies account existence. If the account exists, a single-use,
1-hour-expiring token (SHA-256-hashed at rest, like sessions) is generated
and emailed. `POST /api/auth/password-reset/confirm` consumes the token
(marks it used - replay is rejected) and revokes every existing session.

## Email verification / email change

Same single-use-hashed-token mechanism, 24-hour expiry for verification,
1-hour for an email change. An email change is not applied until the new
address's confirmation link is clicked - the account keeps its old email
until then.

## Account deletion

`DELETE /api/auth/account` is a **hard delete** of the `users` row.
`ON DELETE CASCADE` foreign keys remove every row the account owns in the
same transaction: preferences, sessions, tokens, notifications,
watchlists, paper portfolios, experiments. Past support requests are kept
for operational continuity with `user_id` set to `NULL` (`ON DELETE SET
NULL`); the `contact_email` string already recorded on old tickets is
**not** retroactively scrubbed - a documented, deliberate retention
decision, not an oversight.

## Email

`backend/app/auth/email.py` is a provider-agnostic abstraction with two
adapters:

- **`console`** (default): logs the email content instead of sending it.
  The function returns `delivered=False`, and every caller (registration,
  password reset, the contact form) uses that flag to phrase its response
  honestly - **this codebase never claims an email was sent unless
  `EMAIL_PROVIDER=smtp` is actually configured with real, working
  credentials.**
- **`smtp`**: sends via a real SMTP server using `SMTP_HOST`/`SMTP_PORT`/
  `SMTP_USERNAME`/`SMTP_PASSWORD`. Falls back to logging (not silently
  dropping) if credentials are incomplete.

## Authorization / IDOR prevention

See [SECURITY.md](SECURITY.md) for the full ownership-enforcement pattern
used across watchlists, paper portfolios, and experiments.

## Admin role

`User.role` is `USER` or `ADMIN`. `app.auth.dependencies.require_admin`
enforces it server-side; a non-admin hitting an admin route gets the same
401 shape as an unauthenticated request, rather than a 403 that would
confirm the route exists. There is no signup path to become an admin -
promotion is a manual database update (`UPDATE users SET role='ADMIN'
WHERE email=...`), by design, since this is a minimal foundation, not a
role-management product.
