from __future__ import annotations

import httpx

from netsuite_shim._retry import calculate_backoff, parse_retry_after


class TestCalculateBackoff:
    def test_uses_retry_after_when_present(self):
        assert calculate_backoff(0, retry_after=5.0) == 5.0
        assert calculate_backoff(3, retry_after=10.0) == 10.0

    def test_exponential_backoff_when_no_retry_after(self):
        assert calculate_backoff(0, None, backoff_factor=1.0) == 1.0
        assert calculate_backoff(1, None, backoff_factor=1.0) == 2.0
        assert calculate_backoff(2, None, backoff_factor=1.0) == 4.0
        assert calculate_backoff(3, None, backoff_factor=1.0) == 8.0

    def test_custom_backoff_factor(self):
        assert calculate_backoff(0, None, backoff_factor=0.5) == 0.5
        assert calculate_backoff(2, None, backoff_factor=0.5) == 2.0


class TestParseRetryAfter:
    def test_numeric_value(self):
        resp = httpx.Response(429, headers={"Retry-After": "5"})
        assert parse_retry_after(resp) == 5.0

    def test_float_value(self):
        resp = httpx.Response(429, headers={"Retry-After": "2.5"})
        assert parse_retry_after(resp) == 2.5

    def test_missing_header(self):
        resp = httpx.Response(429)
        assert parse_retry_after(resp) is None

    def test_invalid_value(self):
        resp = httpx.Response(429, headers={"Retry-After": "not-a-number"})
        assert parse_retry_after(resp) is None
