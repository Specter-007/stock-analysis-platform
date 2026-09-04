"""app.request_id: every response carries a correlation id, a caller-
supplied id is echoed back when it looks safe, a malformed one is replaced
rather than trusted verbatim, and log records emitted while handling a
request carry that same id (see app/utils/logging_config.py).
"""
import logging

from app.request_id import REQUEST_ID_HEADER, RequestIDLogFilter, _request_id_ctx, get_request_id


def test_response_always_carries_a_request_id(api_client):
    resp = api_client.get("/api/health")
    assert REQUEST_ID_HEADER in resp.headers
    assert len(resp.headers[REQUEST_ID_HEADER]) > 0


def test_two_requests_get_different_ids(api_client):
    first = api_client.get("/api/health").headers[REQUEST_ID_HEADER]
    second = api_client.get("/api/health").headers[REQUEST_ID_HEADER]
    assert first != second


def test_a_well_formed_caller_supplied_id_is_echoed_back(api_client):
    resp = api_client.get("/api/health", headers={REQUEST_ID_HEADER: "trace-abc123"})
    assert resp.headers[REQUEST_ID_HEADER] == "trace-abc123"


def test_a_malformed_caller_supplied_id_is_replaced_not_trusted(api_client):
    malicious = "not safe\r\nX-Injected: evil"
    resp = api_client.get("/api/health", headers={REQUEST_ID_HEADER: malicious})
    assert resp.headers[REQUEST_ID_HEADER] != malicious
    assert "\r" not in resp.headers[REQUEST_ID_HEADER]


def test_an_overlong_caller_supplied_id_is_replaced(api_client):
    resp = api_client.get("/api/health", headers={REQUEST_ID_HEADER: "a" * 500})
    assert resp.headers[REQUEST_ID_HEADER] != "a" * 500


def test_request_id_log_filter_stamps_the_current_contextvar_onto_records():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", None, None)
    filt = RequestIDLogFilter()

    assert get_request_id() == "-"  # outside any request
    filt.filter(record)
    assert record.request_id == "-"

    token = _request_id_ctx.set("abc-123")
    try:
        filt.filter(record)
        assert record.request_id == "abc-123"
    finally:
        _request_id_ctx.reset(token)


def test_request_id_is_reset_after_the_request_completes(api_client):
    api_client.get("/api/health")
    # The contextvar must not leak into whatever handles the *next* thing on
    # this thread/task once the request that set it has finished.
    assert get_request_id() == "-"
