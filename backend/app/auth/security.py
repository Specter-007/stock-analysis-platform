"""Password hashing, opaque token generation, and CSRF token signing.

Password hashing: Argon2id via argon2-cffi (argon2.PasswordHasher's default
`type` is Argon2id as of argon2-cffi >= 19), the OWASP-recommended default
for new applications. Never a manually-implemented hash (bare SHA-256/MD5).

Session / password-reset / email-verification tokens: a high-entropy random
opaque value (secrets.token_urlsafe) is what the client actually holds (in
a cookie, or embedded in an emailed link); only its SHA-256 hash is ever
persisted, so a database read alone can never be replayed as a live
credential. This mirrors how the password itself is stored.

CSRF: a signed, timestamped token (itsdangerous) bound to the session id -
see app.auth.dependencies.require_csrf for the double-submit-cookie check.
"""
from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.settings import SESSION_SECRET

_hasher = PasswordHasher()

CSRF_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days - refreshed on every login
_csrf_serializer = URLSafeTimedSerializer(SESSION_SECRET, salt="csrf-token")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True if the stored hash was made with weaker-than-current parameters
    (e.g. after an argon2-cffi default upgrade) - callers may opportunistically
    re-hash on a successful login. Never treated as a security failure on its
    own; only used to keep hashes current over time."""
    return _hasher.check_needs_rehash(password_hash)


def generate_opaque_token() -> str:
    """A raw, high-entropy token to hand to the client (session cookie value,
    or the token embedded in a password-reset/email-verification link)."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """SHA-256 hex digest - the only form of the token ever stored server-side."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def sign_csrf_token(session_id: str) -> str:
    return _csrf_serializer.dumps(session_id)


def verify_csrf_token(token: str, session_id: str) -> bool:
    try:
        payload = _csrf_serializer.loads(token, max_age=CSRF_TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return False
    return payload == session_id
