from __future__ import annotations

import pytest
import respx
from httpx import Response

from netsuite_shim import (
    NetSuiteClient,
    NetSuiteConfig,
    TBAConfig,
)
from netsuite_shim.exceptions import (
    NotFoundError,
    ServerError,
    ValidationError,
)

BASE_URL = "https://123456.suitetalk.api.netsuite.com"


class TestNetSuiteConfig:
    def test_requires_auth(self):
        with pytest.raises(ValueError, match="Exactly one"):
            NetSuiteConfig(account_id="123456")

    def test_rejects_both_auth(self):
        with pytest.raises(ValueError, match="Only one"):
            NetSuiteConfig(
                account_id="123456",
                tba=TBAConfig(
                    consumer_key="a",
                    consumer_secret="b",
                    token_key="c",
                    token_secret="d",
                ),
                oauth2={"client_id": "x", "certificate_id": "y", "private_key_path": "/tmp/k"},
            )

    def test_computed_base_url(self, tba_config: NetSuiteConfig):
        assert tba_config.computed_base_url == BASE_URL

    def test_computed_base_url_sandbox(self):
        config = NetSuiteConfig(
            account_id="123456_SB1",
            tba=TBAConfig(
                consumer_key="a",
                consumer_secret="b",
                token_key="c",
                token_secret="d",
            ),
        )
        assert config.computed_base_url == "https://123456-sb1.suitetalk.api.netsuite.com"

    def test_custom_base_url(self):
        config = NetSuiteConfig(
            account_id="123456",
            base_url="https://custom.example.com/",
            tba=TBAConfig(
                consumer_key="a",
                consumer_secret="b",
                token_key="c",
                token_secret="d",
            ),
        )
        assert config.computed_base_url == "https://custom.example.com"


class TestClientLifecycle:
    def test_context_manager(self, tba_config: NetSuiteConfig):
        with NetSuiteClient(tba_config) as client:
            assert client._sync_client is None  # lazy
        # after exit, if sync was used it would be closed

    def test_sub_apis_available(self, client: NetSuiteClient):
        assert hasattr(client, "rest")
        assert hasattr(client, "suiteql")
        assert hasattr(client, "metadata")


class TestRequestSync:
    def test_successful_get(self, client: NetSuiteClient):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.get("/services/rest/record/v1/customer/42").mock(
                return_value=Response(200, json={"id": 42, "companyName": "Acme"})
            )
            result = client._request_sync("GET", "/services/rest/record/v1/customer/42")
            assert result["id"] == 42

    def test_204_returns_empty_dict(self, client: NetSuiteClient):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.patch("/services/rest/record/v1/customer/42").mock(
                return_value=Response(204)
            )
            result = client._request_sync(
                "PATCH", "/services/rest/record/v1/customer/42", json={"name": "New"}
            )
            assert result == {}

    def test_400_raises_validation_error(self, client: NetSuiteClient):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.post("/services/rest/record/v1/customer").mock(
                return_value=Response(400, json={
                    "type": "error",
                    "title": "Invalid field",
                    "status": 400,
                    "o:errorCode": "INVALID_FLD",
                })
            )
            with pytest.raises(ValidationError) as exc_info:
                client._request_sync(
                    "POST", "/services/rest/record/v1/customer", json={"bad": "data"}
                )
            assert exc_info.value.error_code == "INVALID_FLD"

    def test_404_raises_not_found(self, client: NetSuiteClient):
        with respx.mock(base_url=BASE_URL) as mock:
            mock.get("/services/rest/record/v1/customer/999").mock(
                return_value=Response(404, json={
                    "type": "error",
                    "title": "Not found",
                    "status": 404,
                })
            )
            with pytest.raises(NotFoundError):
                client._request_sync("GET", "/services/rest/record/v1/customer/999")

    def test_500_retries_then_raises(self, tba_config: NetSuiteConfig):
        tba_config.max_retries = 1
        tba_config.retry_backoff_factor = 0.0  # no waiting in tests
        client = NetSuiteClient(tba_config)
        with respx.mock(base_url=BASE_URL) as mock:
            route = mock.get("/services/rest/record/v1/customer/1").mock(
                return_value=Response(500, json={
                    "type": "error",
                    "title": "Server error",
                    "status": 500,
                })
            )
            with pytest.raises(ServerError):
                client._request_sync("GET", "/services/rest/record/v1/customer/1")
            assert route.call_count == 2  # initial + 1 retry
