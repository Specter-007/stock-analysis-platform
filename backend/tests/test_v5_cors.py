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
