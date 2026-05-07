from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
import httpx
from fastapi.testclient import TestClient

from app.brightspace.oauth_client import BrightspaceOAuthClient, BrightspaceOAuthConfig
from app.brightspace.token_store import EncryptedRefreshTokenStore
from app.main import create_app


def _build_client(tmp_path: Path, transport: httpx.MockTransport, sleeps: list[float] | None = None):
    config = BrightspaceOAuthConfig(
        tenant="sandbox",
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="https://tool.example.com/callback",
        scopes=("core:*:*",),
        lp_version="1.51",
    )
    key = Fernet.generate_key().decode("utf-8")
    store = EncryptedRefreshTokenStore(tmp_path / "tokens.db", key)
    sleep_calls = sleeps if sleeps is not None else []
    client = BrightspaceOAuthClient(
        config=config,
        token_store=store,
        http_client=httpx.Client(transport=transport),
        sleep=sleep_calls.append,
    )
    return client, store, sleep_calls


def test_build_authorization_url_includes_expected_oauth_params(tmp_path: Path) -> None:
    client, _, _ = _build_client(tmp_path, httpx.MockTransport(lambda _: httpx.Response(200)))

    url = client.build_authorization_url("state-123")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.path.endswith("/auth/oauth2/auth")
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == ["https://tool.example.com/callback"]
    assert query["state"] == ["state-123"]


def test_refresh_tokens_are_encrypted_at_rest(tmp_path: Path) -> None:
    key = Fernet.generate_key().decode("utf-8")
    store = EncryptedRefreshTokenStore(tmp_path / "tokens.db", key)
    store.save_refresh_token("sandbox", "service", "refresh-token-plain")

    with sqlite3.connect(tmp_path / "tokens.db") as conn:
        row = conn.execute(
            "SELECT refresh_token_encrypted FROM app_brightspace_tokens WHERE tenant = ? AND token_owner = ?",
            ("sandbox", "service"),
        ).fetchone()

    assert row is not None
    assert row[0] != "refresh-token-plain"
    assert store.get_refresh_token("sandbox", "service") == "refresh-token-plain"


def test_whoami_refreshes_expired_token_and_retries_transient_failures(tmp_path: Path) -> None:
    responses = iter(
        [
            {"access_token": "expired-access", "refresh_token": "refresh-1", "expires_in": 0},
            {"access_token": "fresh-access", "refresh_token": "refresh-2", "expires_in": 3600},
            503,
            429,
            {"Identifier": 7, "DisplayName": "Instructor"},
        ]
    )
    bearer_tokens: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        next_item = next(responses)
        if request.url.path == "/auth/token":
            assert request.method == "POST"
            assert isinstance(next_item, dict)
            return httpx.Response(200, json=next_item)
        if request.url.path.endswith("/users/whoami"):
            bearer_tokens.append(request.headers["Authorization"])
            if isinstance(next_item, int):
                return httpx.Response(next_item, json={"error": "retry"})
            return httpx.Response(200, json=next_item)
        return httpx.Response(404)

    sleep_calls: list[float] = []
    client, _, _ = _build_client(tmp_path, httpx.MockTransport(handler), sleep_calls)
    client.exchange_code_for_tokens("auth-code", "service")

    whoami = client.whoami("service")

    assert whoami["Identifier"] == 7
    assert bearer_tokens == ["Bearer fresh-access", "Bearer fresh-access", "Bearer fresh-access"]
    assert sleep_calls == [0.25, 0.5]


def test_callback_handler_exchanges_code_and_returns_ok(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            return httpx.Response(
                200,
                json={"access_token": "access", "refresh_token": "refresh", "expires_in": 3600},
            )
        return httpx.Response(404)

    oauth_client, store, _ = _build_client(tmp_path, httpx.MockTransport(handler))
    app = create_app(client=oauth_client)

    with TestClient(app) as test_client:
        response = test_client.get(
            "/brightspace/oauth/callback",
            params={"code": "abc", "state": "s1", "token_owner": "service"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "state": "s1"}
    assert store.get_refresh_token("sandbox", "service") == "refresh"
