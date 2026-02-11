from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)

from netsuite_shim.auth.oauth2 import OAuth2Auth
from netsuite_shim.models import OAuth2Config


@pytest.fixture
def ec_key_path(tmp_path: Path) -> Path:
    """Generate a temporary EC private key for testing."""
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    key_file = tmp_path / "test_key.pem"
    key_file.write_bytes(pem)
    return key_file


@pytest.fixture
def oauth2_config(ec_key_path: Path) -> OAuth2Config:
    return OAuth2Config(
        client_id="test_client_id",
        certificate_id="test_cert_id",
        private_key_path=ec_key_path,
        scopes=["restlets", "rest_webservices"],
        algorithm="ES256",
    )


@pytest.fixture
def oauth2_auth(oauth2_config: OAuth2Config) -> OAuth2Auth:
    return OAuth2Auth(oauth2_config, account_id="123456")


class TestOAuth2Auth:
    def test_token_url(self, oauth2_auth: OAuth2Auth):
        assert oauth2_auth._token_url == (
            "https://123456.suitetalk.api.netsuite.com"
            "/services/rest/auth/oauth2/v1/token"
        )

    def test_token_url_sandbox(self, oauth2_config: OAuth2Config):
        auth = OAuth2Auth(oauth2_config, account_id="123456_SB1")
        assert "123456-sb1" in auth._token_url

    def test_is_token_valid_initially_false(self, oauth2_auth: OAuth2Auth):
        assert not oauth2_auth._is_token_valid()

    @patch("netsuite_shim.auth.oauth2.time")
    def test_is_token_valid_after_store(self, mock_time, oauth2_auth: OAuth2Auth):
        mock_time.time.return_value = 1700000000.0
        oauth2_auth._access_token = "test_token"
        oauth2_auth._expires_at = 1700003600.0  # 1 hour from now
        assert oauth2_auth._is_token_valid()

    @patch("netsuite_shim.auth.oauth2.time")
    def test_is_token_invalid_near_expiry(self, mock_time, oauth2_auth: OAuth2Auth):
        mock_time.time.return_value = 1700003550.0  # 50s before expiry (< 60s buffer)
        oauth2_auth._access_token = "test_token"
        oauth2_auth._expires_at = 1700003600.0
        assert not oauth2_auth._is_token_valid()

    def test_build_jwt_contains_expected_claims(self, oauth2_auth: OAuth2Auth):
        token = oauth2_auth._build_jwt()
        # Decode without verification to inspect claims
        claims = pyjwt.decode(token, options={"verify_signature": False})
        assert claims["iss"] == "test_client_id"
        assert claims["scope"] == ["restlets", "rest_webservices"]
        assert "exp" in claims
        assert "iat" in claims
        assert "jti" in claims

    def test_build_jwt_has_correct_headers(self, oauth2_auth: OAuth2Auth):
        token = oauth2_auth._build_jwt()
        headers = pyjwt.get_unverified_header(token)
        assert headers["kid"] == "test_cert_id"
        assert headers["typ"] == "JWT"
        assert headers["alg"] == "ES256"

    def test_build_token_request(self, oauth2_auth: OAuth2Auth):
        req = oauth2_auth._build_token_request()
        assert req.method == "POST"
        assert "oauth2/v1/token" in str(req.url)
        assert req.headers["Content-Type"] == "application/x-www-form-urlencoded"
