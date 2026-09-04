"""Per-request correlation id: generates one (or reuses a caller-supplied
one) per request, exposes it on the response as `X-Request-ID`, and makes
it available to every log line emitted while handling that request - so a
user-reported error (or an upstream proxy/CDN's own request id) can be
grepped straight to the relevant server logs, without standing up a full
tracing system this app's current scale doesn't need.
"""
from __future__ import annotations

import logging
import re
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

REQUEST_ID_HEADER = "X-Request-ID"

# A caller-supplied id (e.g. from an upstream proxy/CDN) is echoed back so
# it can be correlated across systems, but only if it looks like a
# reasonable token - an attacker-controlled value otherwise flows straight
# into every log line for that request and back out in a response header.
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def get_request_id() -> str:
    return _request_id_ctx.get()


class RequestIDLogFilter(logging.Filter):
    """Injects the current request's id as `%(request_id)s` for the log
    formatter - a no-op ("-") outside of a request (startup/shutdown/
    background code)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming if incoming and _SAFE_ID_RE.match(incoming) else str(uuid.uuid4())
        token = _request_id_ctx.set(request_id)
        try:
            response: Response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
