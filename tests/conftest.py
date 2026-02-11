from __future__ import annotations

import pytest
import respx

from netsuite_shim import NetSuiteClient, NetSuiteConfig, TBAConfig

BASE_URL = "https://123456.suitetalk.api.netsuite.com"


@pytest.fixture
def tba_config() -> NetSuiteConfig:
    return NetSuiteConfig(
        account_id="123456",
        tba=TBAConfig(
            consumer_key="ck_test",
            consumer_secret="cs_test",
            token_key="tk_test",
            token_secret="ts_test",
        ),
    )


@pytest.fixture
def client(tba_config: NetSuiteConfig) -> NetSuiteClient:
    with NetSuiteClient(tba_config) as c:
        yield c


@pytest.fixture
def mock_api():
    with respx.mock(base_url=BASE_URL) as mock:
        yield mock
