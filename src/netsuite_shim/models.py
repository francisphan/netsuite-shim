from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings


# ---------------------------------------------------------------------------
# Auth configuration
# ---------------------------------------------------------------------------


class TBAConfig(BaseModel):
    """OAuth 1.0 Token-Based Authentication credentials."""

    consumer_key: str
    consumer_secret: str
    token_key: str
    token_secret: str


class OAuth2Config(BaseModel):
    """OAuth 2.0 Client Credentials (M2M) configuration."""

    client_id: str
    certificate_id: str
    private_key_path: Path
    scopes: list[str] = Field(default=["restlets", "rest_webservices"])
    algorithm: str = "ES256"


# ---------------------------------------------------------------------------
# Top-level configuration
# ---------------------------------------------------------------------------


class NetSuiteConfig(BaseSettings):
    """Top-level configuration.  Exactly one of *tba* or *oauth2* must be set."""

    account_id: str
    tba: TBAConfig | None = None
    oauth2: OAuth2Config | None = None
    base_url: str | None = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff_factor: float = 1.0

    model_config = {"env_prefix": "NETSUITE_", "env_nested_delimiter": "__"}

    @model_validator(mode="after")
    def _check_auth(self) -> NetSuiteConfig:
        if not self.tba and not self.oauth2:
            raise ValueError("Exactly one of tba or oauth2 must be provided")
        if self.tba and self.oauth2:
            raise ValueError("Only one of tba or oauth2 may be provided")
        return self

    @property
    def computed_base_url(self) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        acct = self.account_id.lower().replace("_", "-")
        return f"https://{acct}.suitetalk.api.netsuite.com"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PaginatedResponse(BaseModel):
    """Generic paginated list response from REST or SuiteQL."""

    count: int | None = None
    has_more: bool = Field(alias="hasMore", default=False)
    items: list[dict[str, Any]] = []
    total_results: int | None = Field(alias="totalResults", default=None)
    links: list[dict[str, Any]] = []
    offset: int = 0

    model_config = {"populate_by_name": True}


class NetSuiteErrorDetail(BaseModel):
    detail: str = ""
    error_code: str = Field(alias="o:errorCode", default="")
    error_path: str | None = Field(alias="o:errorPath", default=None)

    model_config = {"populate_by_name": True}


class NetSuiteErrorResponse(BaseModel):
    type: str = ""
    title: str = ""
    status: int = 0
    error_code: str = Field(alias="o:errorCode", default="")
    error_details: list[NetSuiteErrorDetail] = Field(
        alias="o:errorDetails", default_factory=list
    )

    model_config = {"populate_by_name": True}
