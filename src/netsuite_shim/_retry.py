from __future__ import annotations

import httpx


def calculate_backoff(
    attempt: int,
    retry_after: float | None,
    backoff_factor: float = 1.0,
) -> float:
    """Return seconds to wait.  Prefer *Retry-After* header value if present."""
    if retry_after is not None:
        return retry_after
    return backoff_factor * (2**attempt)


def parse_retry_after(response: httpx.Response) -> float | None:
    """Parse the ``Retry-After`` header (seconds)."""
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None
