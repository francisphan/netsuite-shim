from __future__ import annotations

from typing import Any


class NetSuiteError(Exception):
    """Base exception for all netsuite-shim errors."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        error_code: str | None = None,
        error_details: list[dict[str, Any]] | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.error_details = error_details or []


class AuthenticationError(NetSuiteError):
    """401 — invalid credentials or expired token."""


class AuthorizationError(NetSuiteError):
    """403 — insufficient permissions."""


class NotFoundError(NetSuiteError):
    """404 — record or resource does not exist."""


class ValidationError(NetSuiteError):
    """400 — invalid request body, field values, etc."""


class ConcurrencyLimitError(NetSuiteError):
    """429 — too many requests / concurrency governance limit."""

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs: Any):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(NetSuiteError):
    """5xx — NetSuite server-side error."""


class ConfigurationError(NetSuiteError):
    """Raised when configuration is invalid or missing."""


STATUS_EXCEPTION_MAP: dict[int, type[NetSuiteError]] = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthorizationError,
    404: NotFoundError,
    429: ConcurrencyLimitError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
}
