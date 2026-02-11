from __future__ import annotations

import httpx

from netsuite_shim.client import NetSuiteClient
from netsuite_shim.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConcurrencyLimitError,
    NetSuiteError,
    NotFoundError,
    ServerError,
    ValidationError,
)


def _make_response(status: int, json_body: dict | None = None) -> httpx.Response:
    if json_body is not None:
        return httpx.Response(status, json=json_body)
    return httpx.Response(status, text="error")


class TestBuildException:
    def test_400_validation_error(self):
        resp = _make_response(400, {
            "type": "error",
            "title": "Invalid field value",
            "status": 400,
            "o:errorCode": "INVALID_FIELD",
            "o:errorDetails": [
                {"detail": "Field 'email' is required", "o:errorCode": "MISSING_FIELD"}
            ],
        })
        exc = NetSuiteClient._build_exception(resp)
        assert isinstance(exc, ValidationError)
        assert exc.status == 400
        assert exc.error_code == "INVALID_FIELD"
        assert len(exc.error_details) == 1
        assert exc.error_details[0]["detail"] == "Field 'email' is required"

    def test_401_authentication_error(self):
        resp = _make_response(401, {
            "type": "error",
            "title": "Invalid credentials",
            "status": 401,
            "o:errorCode": "INVALID_LOGIN",
        })
        exc = NetSuiteClient._build_exception(resp)
        assert isinstance(exc, AuthenticationError)
        assert "Invalid credentials" in str(exc)

    def test_403_authorization_error(self):
        resp = _make_response(403, {
            "type": "error",
            "title": "Permission denied",
            "status": 403,
        })
        exc = NetSuiteClient._build_exception(resp)
        assert isinstance(exc, AuthorizationError)

    def test_404_not_found(self):
        resp = _make_response(404, {
            "type": "error",
            "title": "Record not found",
            "status": 404,
            "o:errorCode": "RCRD_DSNT_EXIST",
        })
        exc = NetSuiteClient._build_exception(resp)
        assert isinstance(exc, NotFoundError)
        assert exc.error_code == "RCRD_DSNT_EXIST"

    def test_429_concurrency_limit(self):
        resp = httpx.Response(
            429,
            json={
                "type": "error",
                "title": "Request limit exceeded",
                "status": 429,
            },
            headers={"Retry-After": "5"},
        )
        exc = NetSuiteClient._build_exception(resp)
        assert isinstance(exc, ConcurrencyLimitError)
        assert exc.retry_after == 5.0

    def test_500_server_error(self):
        resp = _make_response(500, {
            "type": "error",
            "title": "Unexpected error",
            "status": 500,
        })
        exc = NetSuiteClient._build_exception(resp)
        assert isinstance(exc, ServerError)

    def test_malformed_json_fallback(self):
        resp = httpx.Response(502, text="Bad Gateway")
        exc = NetSuiteClient._build_exception(resp)
        assert isinstance(exc, NetSuiteError)
        assert exc.status == 502

    def test_unknown_status_code(self):
        resp = _make_response(418, {
            "type": "error",
            "title": "I'm a teapot",
            "status": 418,
        })
        exc = NetSuiteClient._build_exception(resp)
        assert isinstance(exc, NetSuiteError)
        assert not isinstance(exc, ValidationError)
