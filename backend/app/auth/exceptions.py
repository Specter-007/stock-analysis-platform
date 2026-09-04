"""Auth/authorization exceptions, mapped to HTTP responses centrally in
app.api.errors - handlers must never leak internal detail (e.g. whether an
email exists) beyond what each error type's message already says.
"""


class AuthError(Exception):
    pass


class InvalidCredentialsError(AuthError):
    """Login failed. Message is always the same generic text regardless of
    whether the email was unknown or the password was wrong."""


class EmailAlreadyRegisteredError(AuthError):
    pass


class AccountNotActiveError(AuthError):
    pass


class InvalidOrExpiredTokenError(AuthError):
    pass


class NotAuthenticatedError(AuthError):
    """No valid session. Distinct from ResourceNotFoundError so route
    dependencies can return 401 (not logged in) vs 404 (logged in, but this
    resource isn't yours or doesn't exist)."""


class ResourceNotFoundError(AuthError):
    """Deliberately used for BOTH 'resource does not exist' and 'resource
    belongs to a different user' - collapsing these into one response
    prevents an authenticated attacker from using response differences to
    enumerate other users' resource IDs (IDOR probing)."""
