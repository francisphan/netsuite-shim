from __future__ import annotations

import asyncio
import threading
import time
import uuid
from typing import AsyncGenerator, Generator

import httpx
import jwt

from .base import NetSuiteAuth
from ..models import OAuth2Config


class OAuth2Auth(NetSuiteAuth):
    """OAuth 2.0 Client Credentials (M2M) with JWT assertion.

    Caches the access token and refreshes it automatically when expired.
    Thread-safe for sync usage, task-safe for async usage.
    """

    requires_response_body = True

    def __init__(self, config: OAuth2Config, account_id: str) -> None:
        self._config = config
        self._account_id = account_id
        self._access_token: str | None = None
        self._expires_at: float = 0.0
        self._sync_lock = threading.Lock()
        self._async_lock: asyncio.Lock | None = None
        self._private_key = config.private_key_path.read_text()

    @property
    def _token_url(self) -> str:
        acct = self._account_id.lower().replace("_", "-")
        return (
            f"https://{acct}.suitetalk.api.netsuite.com"
            f"/services/rest/auth/oauth2/v1/token"
        )

    def _is_token_valid(self) -> bool:
        return self._access_token is not None and time.time() < (self._expires_at - 60)

    def _build_jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self._config.client_id,
            "scope": self._config.scopes,
            "aud": self._token_url,
            "exp": now + 3600,
            "iat": now,
            "jti": str(uuid.uuid4()),
        }
        headers = {
            "typ": "JWT",
            "kid": self._config.certificate_id,
        }
        return jwt.encode(
            payload,
            self._private_key,
            algorithm=self._config.algorithm,
            headers=headers,
        )

    def _build_token_request(self) -> httpx.Request:
        assertion = self._build_jwt()
        return httpx.Request(
            "POST",
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_assertion_type": (
                    "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
                ),
                "client_assertion": assertion,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    def _store_token(self, response: httpx.Response) -> None:
        data = response.json()
        self._access_token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 3600))

    # -- Sync flow --

    def sync_auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        with self._sync_lock:
            if not self._is_token_valid():
                token_response = yield self._build_token_request()
                token_response.read()
                self._store_token(token_response)

        request.headers["Authorization"] = f"Bearer {self._access_token}"
        yield request

    # -- Async flow --

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        async with self._async_lock:
            if not self._is_token_valid():
                token_response = yield self._build_token_request()
                await token_response.aread()
                self._store_token(token_response)

        request.headers["Authorization"] = f"Bearer {self._access_token}"
        yield request
