"""Brightspace OAuth2 client with refresh-token persistence."""

from __future__ import annotations

from dataclasses import dataclass
from time import sleep as default_sleep
import time
from urllib.parse import urlencode

import httpx

from .retry import retry_with_exponential_backoff
from .token_store import EncryptedRefreshTokenStore


@dataclass(frozen=True)
class BrightspaceOAuthConfig:
    tenant: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: tuple[str, ...]
    lp_version: str = "1.51"

    @property
    def brightspace_base_url(self) -> str:
        return f"https://{self.tenant}.brightspace.com"

    @property
    def token_url(self) -> str:
        return f"{self.brightspace_base_url}/auth/token"

    @property
    def authorization_url(self) -> str:
        return f"{self.brightspace_base_url}/auth/oauth2/auth"

    @property
    def api_base_url(self) -> str:
        return f"{self.brightspace_base_url}/d2l/api"


@dataclass
class _TokenBundle:
    access_token: str
    refresh_token: str
    expires_at: float


class BrightspaceOAuthClient:
    """OAuth2 client for Brightspace REST API calls."""

    def __init__(
        self,
        config: BrightspaceOAuthConfig,
        token_store: EncryptedRefreshTokenStore,
        *,
        http_client: httpx.Client | None = None,
        sleep=default_sleep,
    ) -> None:
        self._config = config
        self._store = token_store
        self._http = http_client or httpx.Client(timeout=15.0)
        self._sleep = sleep
        self._token_cache: dict[str, _TokenBundle] = {}

    def build_authorization_url(self, state: str) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self._config.client_id,
                "redirect_uri": self._config.redirect_uri,
                "scope": " ".join(self._config.scopes),
                "state": state,
            }
        )
        return f"{self._config.authorization_url}?{query}"

    def exchange_code_for_tokens(self, code: str, token_owner: str) -> None:
        token_bundle = self._exchange_tokens(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._config.redirect_uri,
            }
        )
        self._store_token_bundle(token_owner, token_bundle)

    def _exchange_tokens(self, payload: dict[str, str]) -> _TokenBundle:
        response = self._http.post(
            self._config.token_url,
            data=payload,
            auth=(self._config.client_id, self._config.client_secret),
        )
        response.raise_for_status()
        body = response.json()
        refresh_token = body.get("refresh_token")
        if not refresh_token:
            raise ValueError("Brightspace token exchange returned no refresh token")
        expires_in = int(body.get("expires_in", 3600))
        return _TokenBundle(
            access_token=body["access_token"],
            refresh_token=refresh_token,
            expires_at=time.time() + max(expires_in - 30, 0),
        )

    def _store_token_bundle(self, token_owner: str, token_bundle: _TokenBundle) -> None:
        self._store.save_refresh_token(
            tenant=self._config.tenant, token_owner=token_owner, refresh_token=token_bundle.refresh_token
        )
        self._token_cache[token_owner] = token_bundle

    def _refresh_access_token(self, token_owner: str) -> str:
        refresh_token = self._store.get_refresh_token(tenant=self._config.tenant, token_owner=token_owner)
        if refresh_token is None:
            raise KeyError(f"No refresh token stored for owner '{token_owner}'")
        token_bundle = self._exchange_tokens({"grant_type": "refresh_token", "refresh_token": refresh_token})
        self._store_token_bundle(token_owner, token_bundle)
        return token_bundle.access_token

    def _get_valid_access_token(self, token_owner: str) -> str:
        token_bundle = self._token_cache.get(token_owner)
        if token_bundle is not None and token_bundle.expires_at > time.time():
            return token_bundle.access_token
        return self._refresh_access_token(token_owner)

    def whoami(self, token_owner: str) -> dict[str, object]:
        endpoint = f"{self._config.api_base_url}/lp/{self._config.lp_version}/users/whoami"
        token = self._get_valid_access_token(token_owner)
        refreshed_after_unauthorized = False

        def call_api() -> httpx.Response:
            nonlocal token, refreshed_after_unauthorized
            response = self._http.get(endpoint, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 401 and not refreshed_after_unauthorized:
                token = self._refresh_access_token(token_owner)
                refreshed_after_unauthorized = True
                response = self._http.get(endpoint, headers={"Authorization": f"Bearer {token}"})
            return response

        response = retry_with_exponential_backoff(
            operation=call_api,
            should_retry=lambda value: isinstance(value, httpx.Response)
            and value.status_code in {429, 503},
            sleep=self._sleep,
        )
        assert isinstance(response, httpx.Response)
        response.raise_for_status()
        return response.json()
