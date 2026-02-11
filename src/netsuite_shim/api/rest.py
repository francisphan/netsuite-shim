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


class RestApi:
    """REST Record CRUD operations.

    Accessed via ``client.rest``.
    """

    def __init__(self, client: NetSuiteClient) -> None:
        self._client = client
        self._base_path = "/services/rest/record/v1"

    def _record_path(self, record_type: str, record_id: str | int | None = None) -> str:
        path = f"{self._base_path}/{record_type}"
        if record_id is not None:
            path = f"{path}/{record_id}"
        return path

    # ---- Sync ----

    def get(
        self,
        record_type: str,
        record_id: str | int,
        *,
        expand_sub_resources: bool = False,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if expand_sub_resources:
            params["expandSubResources"] = "true"
        if fields:
            params["fields"] = ",".join(fields)
        return self._client._request_sync(
            "GET", self._record_path(record_type, record_id), params=params
        )

    def create(self, record_type: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._client._request_sync(
            "POST", self._record_path(record_type), json=body
        )

    def update(
        self, record_type: str, record_id: str | int, body: dict[str, Any]
    ) -> dict[str, Any]:
        return self._client._request_sync(
            "PATCH", self._record_path(record_type, record_id), json=body
        )

    def upsert(
        self, record_type: str, body: dict[str, Any], *, external_id: str
    ) -> dict[str, Any]:
        return self._client._request_sync(
            "PUT", self._record_path(record_type, external_id), json=body
        )

    def delete(self, record_type: str, record_id: str | int) -> None:
        self._client._request_sync(
            "DELETE", self._record_path(record_type, record_id)
        )

    def list(
        self,
        record_type: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        q: str | None = None,
    ) -> PaginatedResponse:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if q:
            params["q"] = q
        raw = self._client._request_sync(
            "GET", self._record_path(record_type), params=params
        )
        return PaginatedResponse.model_validate(raw)

    def list_pages(
        self, record_type: str, *, limit: int = 1000, q: str | None = None
    ) -> SyncPageIterator:
        def fetch(lim: int, off: int) -> PaginatedResponse:
            return self.list(record_type, limit=lim, offset=off, q=q)

        return SyncPageIterator(fetch, limit=limit)

    def list_all(
        self, record_type: str, *, limit: int = 1000, q: str | None = None
    ) -> Iterator[dict[str, Any]]:
        def fetch(lim: int, off: int) -> PaginatedResponse:
            return self.list(record_type, limit=lim, offset=off, q=q)

        return iter_items_sync(fetch, limit=limit)

    # ---- Async ----

    async def aget(
        self,
        record_type: str,
        record_id: str | int,
        *,
        expand_sub_resources: bool = False,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if expand_sub_resources:
            params["expandSubResources"] = "true"
        if fields:
            params["fields"] = ",".join(fields)
        return await self._client._request_async(
            "GET", self._record_path(record_type, record_id), params=params
        )

    async def acreate(self, record_type: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self._client._request_async(
            "POST", self._record_path(record_type), json=body
        )

    async def aupdate(
        self, record_type: str, record_id: str | int, body: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._client._request_async(
            "PATCH", self._record_path(record_type, record_id), json=body
        )

    async def aupsert(
        self, record_type: str, body: dict[str, Any], *, external_id: str
    ) -> dict[str, Any]:
        return await self._client._request_async(
            "PUT", self._record_path(record_type, external_id), json=body
        )

    async def adelete(self, record_type: str, record_id: str | int) -> None:
        await self._client._request_async(
            "DELETE", self._record_path(record_type, record_id)
        )

    async def alist(
        self,
        record_type: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        q: str | None = None,
    ) -> PaginatedResponse:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if q:
            params["q"] = q
        raw = await self._client._request_async(
            "GET", self._record_path(record_type), params=params
        )
        return PaginatedResponse.model_validate(raw)

    def alist_pages(
        self, record_type: str, *, limit: int = 1000, q: str | None = None
    ) -> AsyncPageIterator:
        async def fetch(lim: int, off: int) -> PaginatedResponse:
            return await self.alist(record_type, limit=lim, offset=off, q=q)

        return AsyncPageIterator(fetch, limit=limit)

    async def alist_all(
        self, record_type: str, *, limit: int = 1000, q: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        async def fetch(lim: int, off: int) -> PaginatedResponse:
            return await self.alist(record_type, limit=lim, offset=off, q=q)

        async for item in iter_items_async(fetch, limit=limit):
            yield item
