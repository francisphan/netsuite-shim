from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator

from .._pagination import (
    AsyncPageIterator,
    SyncPageIterator,
    iter_items_async,
    iter_items_sync,
)
from ..models import PaginatedResponse

if TYPE_CHECKING:
    from ..client import NetSuiteClient


class SuiteQLApi:
    """SuiteQL query execution.

    Accessed via ``client.suiteql``.
    """

    def __init__(self, client: NetSuiteClient) -> None:
        self._client = client
        self._path = "/services/rest/query/v1/suiteql"

    # ---- Sync ----

    def query(
        self, sql: str, *, limit: int = 1000, offset: int = 0
    ) -> PaginatedResponse:
        raw = self._client._request_sync(
            "POST",
            self._path,
            params={"limit": limit, "offset": offset},
            json={"q": sql},
            extra_headers={"Prefer": "transient"},
        )
        return PaginatedResponse.model_validate(raw)

    def query_pages(self, sql: str, *, limit: int = 1000) -> SyncPageIterator:
        def fetch(lim: int, off: int) -> PaginatedResponse:
            return self.query(sql, limit=lim, offset=off)

        return SyncPageIterator(fetch, limit=limit)

    def query_all(self, sql: str, *, limit: int = 1000) -> Iterator[dict[str, Any]]:
        def fetch(lim: int, off: int) -> PaginatedResponse:
            return self.query(sql, limit=lim, offset=off)

        return iter_items_sync(fetch, limit=limit)

    # ---- Async ----

    async def aquery(
        self, sql: str, *, limit: int = 1000, offset: int = 0
    ) -> PaginatedResponse:
        raw = await self._client._request_async(
            "POST",
            self._path,
            params={"limit": limit, "offset": offset},
            json={"q": sql},
            extra_headers={"Prefer": "transient"},
        )
        return PaginatedResponse.model_validate(raw)

    def aquery_pages(self, sql: str, *, limit: int = 1000) -> AsyncPageIterator:
        async def fetch(lim: int, off: int) -> PaginatedResponse:
            return await self.aquery(sql, limit=lim, offset=off)

        return AsyncPageIterator(fetch, limit=limit)

    async def aquery_all(
        self, sql: str, *, limit: int = 1000
    ) -> AsyncIterator[dict[str, Any]]:
        async def fetch(lim: int, off: int) -> PaginatedResponse:
            return await self.aquery(sql, limit=lim, offset=off)

        async for item in iter_items_async(fetch, limit=limit):
            yield item
