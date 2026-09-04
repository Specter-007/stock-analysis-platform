"""V5 regression test: CORS preflight must allow every HTTP method any
route actually uses.

Real bug found via live browser testing: the CORS middleware's
allow_methods list only included GET/POST/OPTIONS. Adding the V5
Experiment Lab's PATCH (update notes) and DELETE (delete experiment)
routes meant the browser's preflight OPTIONS request for those methods
was silently rejected (no CORS headers on a non-2xx preflight response),
so the actual PATCH/DELETE request was never even sent - the frontend
reported a generic "could not reach the analysis server" network error
that had nothing to do with the server actually being reachable. This
also affected the pre-existing DELETE /api/watchlist/{ticker} route,
which had presumably never been exercised through an actual browser
(only via server-side TestClient in tests, which never triggers a CORS
preflight at all) - a Python-side test suite alone could not have caught
this class of bug, which is why this test issues a real OPTIONS preflight
request rather than only inspecting the middleware's configured method list.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _preflight_allows(path: str, method: str, origin: str = "http://localhost:3000") -> bool:
    resp = client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type",
        },
    )
    if resp.status_code >= 400:
        return False
    allowed = resp.headers.get("access-control-allow-methods", "")
    return method in [m.strip() for m in allowed.split(",")]


def test_preflight_allows_get():
    assert _preflight_allows("/api/experiments", "GET")


def test_preflight_allows_post():
    assert _preflight_allows("/api/experiments", "POST")


def test_preflight_allows_patch():
    assert _preflight_allows("/api/experiments/exp_test/notes", "PATCH")


def test_preflight_allows_delete_for_experiments():
    assert _preflight_allows("/api/experiments/exp_test", "DELETE")


def test_preflight_allows_delete_for_watchlist():
    """The pre-existing DELETE /api/watchlist/{ticker} route hits the exact
    same CORS gap - included here so a future regression on this method is
    caught regardless of which route exercises it first.
    """
    assert _preflight_allows("/api/watchlist/AAPL", "DELETE")


# --- Final production-hardening pass: an explicitly disallowed origin ---


def test_preflight_from_disallowed_origin_does_not_grant_cors_headers():
    """A request from an origin NOT in CORS_ALLOWED_ORIGINS must not receive
    an Access-Control-Allow-Origin header naming that origin - the browser
    enforces CORS based on this header, so its absence (or a mismatched
    value) is what actually blocks the cross-origin response from being
    read by the malicious page's JavaScript.
    """
    evil_origin = "https://evil.example.com"
    resp = client.options(
        "/api/experiments",
        headers={
            "Origin": evil_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    allow_origin = resp.headers.get("access-control-allow-origin")
    assert allow_origin != evil_origin
    assert allow_origin != "*"


def test_actual_get_request_from_disallowed_origin_lacks_cors_header():
    """Even a real (non-preflight) GET from a disallowed origin must not
    come back with an Access-Control-Allow-Origin naming that origin - the
    request still executes server-side (CORS is enforced by the browser,
    not the server refusing to run the handler), but the browser will
    refuse to expose the response to the page's script without this header.
    """
    resp = client.get("/api/health", headers={"Origin": "https://evil.example.com"})
    allow_origin = resp.headers.get("access-control-allow-origin")
    assert allow_origin != "https://evil.example.com"
    assert allow_origin != "*"


def test_actual_get_request_from_allowed_origin_has_matching_cors_header():
    resp = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
