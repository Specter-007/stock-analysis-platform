"""Rejects oversized or non-standard-JSON request bodies before they reach
routing/validation.

Two independent hardening checks, both added during the final production-
hardening pass's resource-abuse audit:

1. Body size: individual field lengths are already bounded by Pydantic
   schemas (ticker counts, message lengths, etc.) - this is a coarser,
   earlier backstop against a request whose `Content-Length` alone
   indicates it could not possibly be a legitimate payload for this API
   (which has no file-upload endpoints).
2. `NaN`/`Infinity`/`-Infinity` literals: Python's `json` module accepts
   these as a non-standard extension, so a numeric field with a `gt=0`
   constraint correctly rejects `NaN` at the Pydantic level - but
   FastAPI's default validation-error handler then tries to echo the
   rejected value back in the error response, and Starlette's
   `JSONResponse` refuses to serialize `NaN` (`ValueError: Out of range
   float values are not JSON compliant`), turning what should be a clean
   422 into an unhandled 500. Rejecting these tokens at the raw-body level
   turns it into a clean, intentional 422 instead. Found by
   tests/test_input_abuse.py during this audit, not simulated.
"""
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

MAX_REQUEST_BODY_BYTES = 1_000_000  # 1 MB - generous for the largest legitimate JSON body this API accepts


def _reject_non_finite(token: str):
    raise ValueError(f"{token} is not permitted in a request body")


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"error_type": "PAYLOAD_TOO_LARGE", "detail": "Request body exceeds the maximum allowed size."},
                    )
            except ValueError:
                pass  # malformed Content-Length header - let the normal request handling reject it

        if "application/json" in request.headers.get("content-type", ""):
            body = await request.body()  # Starlette caches this; downstream handlers still see the full body.
            if body:
                try:
                    json.loads(body, parse_constant=_reject_non_finite)
                except ValueError:
                    return JSONResponse(
                        status_code=422,
                        content={
                            "error_type": "INVALID_JSON",
                            "detail": "Request body is not valid JSON (NaN/Infinity are not permitted).",
                        },
                    )

        return await call_next(request)
