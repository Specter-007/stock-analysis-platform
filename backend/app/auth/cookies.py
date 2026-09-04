from __future__ import annotations

from fastapi import Response

from app.settings import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, SESSION_COOKIE_SECURE, SESSION_TTL_DAYS

_MAX_AGE_SECONDS = SESSION_TTL_DAYS * 24 * 3600


def set_auth_cookies(response: Response, *, session_token: str, csrf_token: str) -> None:
    # httpOnly session cookie: never readable by JS (defends against session
    # theft via XSS). CSRF cookie is deliberately NOT httpOnly - the frontend
    # must read it to echo it back in the X-CSRF-Token header.
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=_MAX_AGE_SECONDS,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=_MAX_AGE_SECONDS,
        httponly=False,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
