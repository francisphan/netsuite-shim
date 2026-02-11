from __future__ import annotations

import json

import respx
from httpx import Response

from netsuite_shim import NetSuiteClient, NetSuiteConfig, TBAConfig

BASE_URL = "https://123456.suitetalk.api.netsuite.com"


def _make_client() -> NetSuiteClient:
    config = NetSuiteConfig(
        account_id="123456",
        tba=TBAConfig(
            consumer_key="a",
            consumer_secret="b",
            token_key="c",
            token_secret="d",
        ),
    )
    return NetSuiteClient(config)


class TestSuiteQLQuery:
    def test_query_sends_correct_body(self):
        with respx.mock(base_url=BASE_URL) as mock:
            route = mock.post("/services/rest/query/v1/suiteql").mock(
                return_value=Response(200, json={
                    "count": 1,
                    "hasMore": False,
                    "items": [{"id": 1, "companyname": "Acme"}],
                    "totalResults": 1,
                })
            )
            client = _make_client()
            result = client.suiteql.query("SELECT id, companyname FROM customer")

            request = route.calls[0].request
            body = json.loads(request.content)
            assert body == {"q": "SELECT id, companyname FROM customer"}
            assert request.headers.get("Prefer") == "transient"
            assert len(result.items) == 1
            assert result.items[0]["companyname"] == "Acme"

    def test_query_with_pagination_params(self):
        with respx.mock(base_url=BASE_URL) as mock:
            route = mock.post("/services/rest/query/v1/suiteql").mock(
                return_value=Response(200, json={
                    "count": 0, "hasMore": False, "items": [],
                })
            )
            client = _make_client()
            client.suiteql.query("SELECT id FROM customer", limit=50, offset=100)

            url = str(route.calls[0].request.url)
            assert "limit=50" in url
            assert "offset=100" in url

    def test_query_all_paginates(self):
        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Response(200, json={
                    "count": 2,
                    "hasMore": True,
                    "items": [{"id": 1}, {"id": 2}],
                })
            return Response(200, json={
                "count": 1,
                "hasMore": False,
                "items": [{"id": 3}],
            })

        with respx.mock(base_url=BASE_URL) as mock:
            mock.post("/services/rest/query/v1/suiteql").mock(
                side_effect=side_effect
            )
            client = _make_client()
            items = list(client.suiteql.query_all("SELECT id FROM customer", limit=2))
            assert len(items) == 3
