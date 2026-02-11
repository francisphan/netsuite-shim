from __future__ import annotations

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


class TestRestGet:
    def test_get_record(self):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.get("/services/rest/record/v1/customer/42").mock(
                return_value=Response(200, json={"id": 42, "companyName": "Acme"})
            )
            client = _make_client()
            result = client.rest.get("customer", 42)
            assert result["id"] == 42
            assert result["companyName"] == "Acme"

    def test_get_with_fields(self):
        with respx.mock(base_url=BASE_URL) as mock:
            route = mock.get("/services/rest/record/v1/customer/1").mock(
                return_value=Response(200, json={"id": 1, "email": "a@b.com"})
            )
            client = _make_client()
            client.rest.get("customer", 1, fields=["id", "email"])
            assert "fields" in str(route.calls[0].request.url)


class TestRestCreate:
    def test_create_record(self):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.post("/services/rest/record/v1/customer").mock(
                return_value=Response(200, json={"id": 99})
            )
            client = _make_client()
            result = client.rest.create("customer", {"companyName": "NewCo"})
            assert result["id"] == 99


class TestRestUpdate:
    def test_update_record(self):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.patch("/services/rest/record/v1/customer/42").mock(
                return_value=Response(204)
            )
            client = _make_client()
            result = client.rest.update("customer", 42, {"companyName": "Updated"})
            assert result == {}


class TestRestDelete:
    def test_delete_record(self):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.delete("/services/rest/record/v1/customer/42").mock(
                return_value=Response(204)
            )
            client = _make_client()
            client.rest.delete("customer", 42)


class TestRestList:
    def test_list_records(self):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.get("/services/rest/record/v1/customer").mock(
                return_value=Response(200, json={
                    "count": 2,
                    "hasMore": False,
                    "items": [{"id": 1}, {"id": 2}],
                    "links": [],
                })
            )
            client = _make_client()
            page = client.rest.list("customer", limit=10)
            assert len(page.items) == 2
            assert page.has_more is False

    def test_list_all_paginates(self):
        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Response(200, json={
                    "count": 1, "hasMore": True, "items": [{"id": 1}],
                })
            return Response(200, json={
                "count": 1, "hasMore": False, "items": [{"id": 2}],
            })

        with respx.mock(base_url=BASE_URL) as mock:
            mock.get("/services/rest/record/v1/customer").mock(
                side_effect=side_effect
            )
            client = _make_client()
            items = list(client.rest.list_all("customer", limit=1))
            assert len(items) == 2
            assert items[0]["id"] == 1
            assert items[1]["id"] == 2
