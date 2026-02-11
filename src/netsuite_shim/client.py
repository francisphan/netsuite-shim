from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from ._retry import calculate_backoff, parse_retry_after
from .api.metadata import MetadataApi
from .api.rest import RestApi
from .api.suiteql import SuiteQLApi
from .auth.oauth2 import OAuth2Auth
from .auth.tba import TBAAuth
from .exceptions import (
    STATUS_EXCEPTION_MAP,
    ConcurrencyLimitError,
    NetSuiteError,
)
from .models import NetSuiteConfig, NetSuiteErrorResponse


class NetSuiteClient:
    """Unified client for NetSuite REST API, SuiteQL, and metadata.

    Supports both sync and async usage.  Construct with a
    :class:`NetSuiteConfig` instance.

    Sync::

        client = NetSuiteClient(config)
        customer = client.rest.get("customer", 123)
        results = client.suiteql.query("SELECT id, companyname FROM customer")
        client.close()

    Async::

        async with NetSuiteClient(config) as client:
            customer = await client.rest.aget("customer", 123)
    """

    def __init__(self, config: NetSuiteConfig) -> None:
        self._config = config
        self._base_url = config.computed_base_url
        self._auth = self._build_auth(config)
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

        self.rest = RestApi(self)
        self.suiteql = SuiteQLApi(self)
        self.metadata = MetadataApi(self)

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    @staticmethod
    def _build_auth(config: NetSuiteConfig) -> TBAAuth | OAuth2Auth:
        if config.tba:
            return TBAAuth(config.tba, realm=config.account_id)
        if config.oauth2:
            return OAuth2Auth(config.oauth2, account_id=config.account_id)
        raise ValueError("No auth config provided")

    # ------------------------------------------------------------------
    # Lazy httpx clients
    # ------------------------------------------------------------------

    @property
    def _sync(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                base_url=self._base_url,
                auth=self._auth,
                timeout=httpx.Timeout(self._config.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._sync_client

    @property
    def _async(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                base_url=self._base_url,
                auth=self._auth,
                timeout=httpx.Timeout(self._config.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._async_client

    # ------------------------------------------------------------------
    # Core request methods with retry
    # ------------------------------------------------------------------

    def _request_sync(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = dict(extra_headers) if extra_headers else {}
        last_exc: NetSuiteError | None = None

        for attempt in range(self._config.max_retries + 1):
            response = self._sync.request(
                method, path, params=params, json=json, headers=headers
            )
            if response.status_code < 400:
                if response.status_code == 204 or not response.content:
                    return {}
                return response.json()

            exc = self._build_exception(response)

            if response.status_code == 429 and attempt < self._config.max_retries:
                retry_after = parse_retry_after(response)
                wait = calculate_backoff(
                    attempt, retry_after, self._config.retry_backoff_factor
                )
                time.sleep(wait)
                last_exc = exc
                continue

            if response.status_code >= 500 and attempt < self._config.max_retries:
                wait = calculate_backoff(
                    attempt, None, self._config.retry_backoff_factor
                )
                time.sleep(wait)
                last_exc = exc
                continue

            raise exc

        raise last_exc or NetSuiteError("Max retries exceeded")

    async def _request_async(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = dict(extra_headers) if extra_headers else {}
        last_exc: NetSuiteError | None = None

        for attempt in range(self._config.max_retries + 1):
            response = await self._async.request(
                method, path, params=params, json=json, headers=headers
            )
            if response.status_code < 400:
                if response.status_code == 204 or not response.content:
                    return {}
                return response.json()

            exc = self._build_exception(response)

            if response.status_code == 429 and attempt < self._config.max_retries:
                retry_after = parse_retry_after(response)
                wait = calculate_backoff(
                    attempt, retry_after, self._config.retry_backoff_factor
                )
                await asyncio.sleep(wait)
                last_exc = exc
                continue

            if response.status_code >= 500 and attempt < self._config.max_retries:
                wait = calculate_backoff(
                    attempt, None, self._config.retry_backoff_factor
                )
                await asyncio.sleep(wait)
                last_exc = exc
                continue

            raise exc

        raise last_exc or NetSuiteError("Max retries exceeded")

    # ------------------------------------------------------------------
    # Error parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _build_exception(response: httpx.Response) -> NetSuiteError:
        try:
            body = response.json()
            error_resp = NetSuiteErrorResponse.model_validate(body)
        except Exception:
            return NetSuiteError(
                f"HTTP {response.status_code}",
                status=response.status_code,
            )

        exc_class = STATUS_EXCEPTION_MAP.get(response.status_code, NetSuiteError)
        kwargs: dict[str, Any] = {
            "status": error_resp.status or response.status_code,
            "error_code": error_resp.error_code,
            "error_details": [d.model_dump() for d in error_resp.error_details],
        }
        if exc_class is ConcurrencyLimitError:
            kwargs["retry_after"] = parse_retry_after(response)
        return exc_class(
            error_resp.title or f"HTTP {response.status_code}", **kwargs
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()

    async def aclose(self) -> None:
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()

    def __enter__(self) -> NetSuiteClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    async def __aenter__(self) -> NetSuiteClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
