from __future__ import annotations

from typing import Any, AsyncIterator, Awaitable, Callable, Iterator

from .models import PaginatedResponse

DEFAULT_PAGE_SIZE = 1000


class SyncPageIterator:
    """Synchronous iterator over all pages of a paginated NetSuite response."""

    def __init__(
        self,
        fetch_page: Callable[[int, int], PaginatedResponse],
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ):
        self._fetch_page = fetch_page
        self._limit = limit
        self._offset = offset
        self._exhausted = False

    def __iter__(self) -> Iterator[PaginatedResponse]:
        return self

    def __next__(self) -> PaginatedResponse:
        if self._exhausted:
            raise StopIteration
        page = self._fetch_page(self._limit, self._offset)
        if not page.has_more:
            self._exhausted = True
        else:
            self._offset += self._limit
        if not page.items and self._exhausted:
            raise StopIteration
        return page


class AsyncPageIterator:
    """Async iterator over all pages of a paginated NetSuite response."""

    def __init__(
        self,
        fetch_page: Callable[[int, int], Awaitable[PaginatedResponse]],
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ):
        self._fetch_page = fetch_page
        self._limit = limit
        self._offset = offset
        self._exhausted = False

    def __aiter__(self) -> AsyncPageIterator:
        return self

    async def __anext__(self) -> PaginatedResponse:
        if self._exhausted:
            raise StopAsyncIteration
        page = await self._fetch_page(self._limit, self._offset)
        if not page.has_more:
            self._exhausted = True
        else:
            self._offset += self._limit
        if not page.items and self._exhausted:
            raise StopAsyncIteration
        return page


def iter_items_sync(
    fetch_page: Callable[[int, int], PaginatedResponse],
    limit: int = DEFAULT_PAGE_SIZE,
) -> Iterator[dict[str, Any]]:
    """Flatten paginated results into a stream of individual items."""
    for page in SyncPageIterator(fetch_page, limit=limit):
        yield from page.items


async def iter_items_async(
    fetch_page: Callable[[int, int], Awaitable[PaginatedResponse]],
    limit: int = DEFAULT_PAGE_SIZE,
) -> AsyncIterator[dict[str, Any]]:
    """Async flatten paginated results into a stream of individual items."""
    async for page in AsyncPageIterator(fetch_page, limit=limit):
        for item in page.items:
            yield item
