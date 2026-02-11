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


class TestMetadataListRecordTypes:
    def test_list_all_record_types(self):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.get("/services/rest/record/v1/metadata-catalog").mock(
                return_value=Response(200, json={
                    "items": [
                        {"name": "customer", "href": "/customer"},
                        {"name": "invoice", "href": "/invoice"},
                    ],
                })
            )
            client = _make_client()
            result = client.metadata.list_record_types()
            assert len(result["items"]) == 2

    def test_list_with_select(self):
        with respx.mock(base_url=BASE_URL) as mock:
            route = mock.get("/services/rest/record/v1/metadata-catalog").mock(
                return_value=Response(200, json={"items": [{"name": "customer"}]})
            )
            client = _make_client()
            client.metadata.list_record_types(select=["customer", "invoice"])
            url = str(route.calls[0].request.url)
            assert "select" in url


class TestMetadataGetRecordSchema:
    def test_get_schema(self):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.get("/services/rest/record/v1/metadata-catalog/customer").mock(
                return_value=Response(200, json={
                    "type": "object",
                    "title": "Customer",
                    "properties": {
                        "id": {"type": "integer"},
                        "companyName": {"type": "string"},
                    },
                })
            )
            client = _make_client()
            schema = client.metadata.get_record_schema("customer")
            assert schema["title"] == "Customer"
            assert "companyName" in schema["properties"]
