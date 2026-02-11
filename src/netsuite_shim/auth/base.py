from __future__ import annotations

import httpx


class NetSuiteAuth(httpx.Auth):
    """Abstract base for NetSuite auth providers.

    Subclasses implement ``auth_flow`` to inject Authorization headers
    into outgoing requests.  Works transparently with both
    ``httpx.Client`` (sync) and ``httpx.AsyncClient`` (async).
    """
