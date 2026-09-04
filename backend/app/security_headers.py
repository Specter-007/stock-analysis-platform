"""Baseline security response headers for a JSON API.

Kept deliberately permissive on /docs, /redoc, /openapi.json since FastAPI's
built-in Swagger/ReDoc UI loads its JS/CSS from a CDN - a strict CSP there
would silently break the interactive API docs rather than protect anything
(the API itself returns only JSON, never renders untrusted HTML).
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.settings import IS_PRODUCTION

_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
        if request.url.path not in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if IS_PRODUCTION:
            # Only meaningful/safe to send over an actual HTTPS deployment.
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
