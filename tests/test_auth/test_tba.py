from __future__ import annotations

from unittest.mock import patch

import httpx

from netsuite_shim.auth.tba import TBAAuth, _percent_encode
from netsuite_shim.models import TBAConfig


def _make_auth() -> TBAAuth:
    config = TBAConfig(
        consumer_key="ck_abc",
        consumer_secret="cs_secret",
        token_key="tk_xyz",
        token_secret="ts_secret",
    )
    return TBAAuth(config, realm="123456")


class TestPercentEncode:
    def test_basic_string(self):
        assert _percent_encode("hello") == "hello"

    def test_special_chars(self):
        assert _percent_encode("a b") == "a%20b"
        assert _percent_encode("a+b") == "a%2Bb"
        assert _percent_encode("a&b=c") == "a%26b%3Dc"


class TestTBAAuthFlow:
    @patch("netsuite_shim.auth.tba.time")
    @patch("netsuite_shim.auth.tba.secrets")
    def test_auth_flow_sets_authorization_header(self, mock_secrets, mock_time):
        mock_time.time.return_value = 1700000000
        mock_secrets.token_hex.return_value = "abcdef1234567890"

        auth = _make_auth()
        request = httpx.Request("GET", "https://123456.suitetalk.api.netsuite.com/services/rest/record/v1/customer")

        flow = auth.auth_flow(request)
        modified_request = next(flow)

        assert "Authorization" in modified_request.headers
        header = modified_request.headers["Authorization"]
        assert header.startswith("OAuth ")
        assert 'realm="123456"' in header
        assert "oauth_consumer_key" in header
        assert "oauth_token" in header
        assert "oauth_signature" in header
        assert "HMAC-SHA256" in header

    @patch("netsuite_shim.auth.tba.time")
    @patch("netsuite_shim.auth.tba.secrets")
    def test_signature_is_deterministic_with_fixed_inputs(self, mock_secrets, mock_time):
        mock_time.time.return_value = 1700000000
        mock_secrets.token_hex.return_value = "fixednonce"

        auth = _make_auth()
        request1 = httpx.Request("GET", "https://123456.suitetalk.api.netsuite.com/services/rest/record/v1/customer")
        request2 = httpx.Request("GET", "https://123456.suitetalk.api.netsuite.com/services/rest/record/v1/customer")

        flow1 = auth.auth_flow(request1)
        flow2 = auth.auth_flow(request2)
        r1 = next(flow1)
        r2 = next(flow2)

        assert r1.headers["Authorization"] == r2.headers["Authorization"]

    @patch("netsuite_shim.auth.tba.time")
    @patch("netsuite_shim.auth.tba.secrets")
    def test_different_urls_produce_different_signatures(self, mock_secrets, mock_time):
        mock_time.time.return_value = 1700000000
        mock_secrets.token_hex.return_value = "fixednonce"

        auth = _make_auth()
        req_a = httpx.Request("GET", "https://123456.suitetalk.api.netsuite.com/services/rest/record/v1/customer")
        req_b = httpx.Request("GET", "https://123456.suitetalk.api.netsuite.com/services/rest/record/v1/invoice")

        flow_a = auth.auth_flow(req_a)
        flow_b = auth.auth_flow(req_b)
        r_a = next(flow_a)
        r_b = next(flow_b)

        assert r_a.headers["Authorization"] != r_b.headers["Authorization"]

    @patch("netsuite_shim.auth.tba.time")
    @patch("netsuite_shim.auth.tba.secrets")
    def test_query_params_included_in_signature(self, mock_secrets, mock_time):
        mock_time.time.return_value = 1700000000
        mock_secrets.token_hex.return_value = "fixednonce"

        auth = _make_auth()
        req_no_q = httpx.Request("GET", "https://123456.suitetalk.api.netsuite.com/services/rest/record/v1/customer")
        req_with_q = httpx.Request("GET", "https://123456.suitetalk.api.netsuite.com/services/rest/record/v1/customer?limit=10")

        flow1 = auth.auth_flow(req_no_q)
        flow2 = auth.auth_flow(req_with_q)
        r1 = next(flow1)
        r2 = next(flow2)

        # Query params change the signature but not the header keys
        assert r1.headers["Authorization"] != r2.headers["Authorization"]
