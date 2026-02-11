from __future__ import annotations

import pytest

from netsuite_shim._pagination import (
    AsyncPageIterator,
    SyncPageIterator,
    iter_items_async,
    iter_items_sync,
)
from netsuite_shim.models import PaginatedResponse


def _make_page(
    items: list[dict], has_more: bool = False, offset: int = 0
) -> PaginatedResponse:
    return PaginatedResponse(
        count=len(items),
        has_more=has_more,
        items=items,
        offset=offset,
    )


class TestSyncPageIterator:
    def test_single_page(self):
        def fetch(limit: int, offset: int) -> PaginatedResponse:
            return _make_page([{"id": 1}, {"id": 2}], has_more=False)

        pages = list(SyncPageIterator(fetch, limit=10))
        assert len(pages) == 1
        assert len(pages[0].items) == 2

    def test_multiple_pages(self):
        call_count = 0

        def fetch(limit: int, offset: int) -> PaginatedResponse:
            nonlocal call_count
            call_count += 1
            if offset == 0:
                return _make_page([{"id": 1}], has_more=True, offset=0)
            else:
                return _make_page([{"id": 2}], has_more=False, offset=10)

        pages = list(SyncPageIterator(fetch, limit=10))
        assert len(pages) == 2
        assert call_count == 2

    def test_empty_first_page(self):
        def fetch(limit: int, offset: int) -> PaginatedResponse:
            return _make_page([], has_more=False)

        pages = list(SyncPageIterator(fetch, limit=10))
        assert len(pages) == 0

    def test_offsets_increment_correctly(self):
        offsets_seen: list[int] = []

        def fetch(limit: int, offset: int) -> PaginatedResponse:
            offsets_seen.append(offset)
            if len(offsets_seen) < 3:
                return _make_page([{"id": len(offsets_seen)}], has_more=True)
            return _make_page([{"id": len(offsets_seen)}], has_more=False)

        list(SyncPageIterator(fetch, limit=25))
        assert offsets_seen == [0, 25, 50]


class TestIterItemsSync:
    def test_flattens_multiple_pages(self):
        def fetch(limit: int, offset: int) -> PaginatedResponse:
            if offset == 0:
                return _make_page([{"id": 1}, {"id": 2}], has_more=True)
            return _make_page([{"id": 3}], has_more=False)

        items = list(iter_items_sync(fetch, limit=10))
        assert items == [{"id": 1}, {"id": 2}, {"id": 3}]


class TestAsyncPageIterator:
    @pytest.mark.asyncio
    async def test_single_page(self):
        async def fetch(limit: int, offset: int) -> PaginatedResponse:
            return _make_page([{"id": 1}], has_more=False)

        pages = [page async for page in AsyncPageIterator(fetch, limit=10)]
        assert len(pages) == 1

    @pytest.mark.asyncio
    async def test_multiple_pages(self):
        async def fetch(limit: int, offset: int) -> PaginatedResponse:
            if offset == 0:
                return _make_page([{"id": 1}], has_more=True)
            return _make_page([{"id": 2}], has_more=False)

        pages = [page async for page in AsyncPageIterator(fetch, limit=10)]
        assert len(pages) == 2


class TestIterItemsAsync:
    @pytest.mark.asyncio
    async def test_flattens(self):
        async def fetch(limit: int, offset: int) -> PaginatedResponse:
            if offset == 0:
                return _make_page([{"id": 1}, {"id": 2}], has_more=True)
            return _make_page([{"id": 3}], has_more=False)

        items = [item async for item in iter_items_async(fetch, limit=10)]
        assert items == [{"id": 1}, {"id": 2}, {"id": 3}]
