from __future__ import annotations

from datetime import UTC, datetime, timedelta
import re

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.lti.config import get_lti_settings, get_tool_conf
from app.lti.routes import configure_oidc_store
from app.main import app


@pytest.fixture()
def keypair() -> tuple[str, str]:
    return _generate_rsa_keypair()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, keypair: tuple[str, str]) -> TestClient:
    _, platform_public_key = keypair
    tool_private_key, tool_public_key = _generate_rsa_keypair()
    monkeypatch.setenv("LTI_ISSUER", "https://sandbox.brightspace.com")
    monkeypatch.setenv("LTI_CLIENT_ID", "client-123")
    monkeypatch.setenv("LTI_DEPLOYMENT_ID", "deployment-abc")
    monkeypatch.setenv("LTI_AUTH_LOGIN_URL", "https://sandbox.brightspace.com/d2l/lti/auth")
    monkeypatch.setenv("LTI_LAUNCH_URL", "https://tool.example/api/lti/launch")
    monkeypatch.setenv("LTI_PLATFORM_PUBLIC_KEY_PEM", platform_public_key)
    monkeypatch.setenv("LTI_TOOL_PRIVATE_KEY_PEM", tool_private_key)
    monkeypatch.setenv("LTI_TOOL_PUBLIC_KEY_PEM", tool_public_key)
    get_lti_settings.cache_clear()
    get_tool_conf.cache_clear()
    configure_oidc_store(get_lti_settings())
    return TestClient(app)


def _launch_params(client: TestClient) -> tuple[str, str]:
    response = client.get(
        "/api/lti/login",
        params={
            "iss": "https://sandbox.brightspace.com",
            "login_hint": "hint",
            "target_link_uri": "https://tool.example/api/lti/launch",
            "lti_message_hint": "msg",
            "client_id": "client-123",
        },
    )
    assert response.status_code == 200
    state = re.search(r'name="state" value="([^"]+)"', response.text)
    nonce = re.search(r'name="nonce" value="([^"]+)"', response.text)
    assert state is not None
    assert nonce is not None
    return state.group(1), nonce.group(1)


def _make_token(private_key_pem: str, nonce: str, roles: list[str]) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": "https://sandbox.brightspace.com",
        "aud": "client-123",
        "sub": "user-42",
        "nonce": nonce,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id": "deployment-abc",
        "https://purl.imsglobal.org/spec/lti/claim/context": {"id": "6606"},
        "https://purl.imsglobal.org/spec/lti/claim/resource_link": {"id": "resource-1"},
        "https://purl.imsglobal.org/spec/lti/claim/roles": roles,
    }
    return jwt.encode(payload, private_key_pem, algorithm="RS256")


def test_jwks_endpoint_returns_public_key(client: TestClient) -> None:
    response = client.get("/api/lti/jwks")

    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) == 1
    assert data["keys"][0]["kty"] == "RSA"
    assert data["keys"][0]["kid"] == "um-ai-tool-key"


def test_oidc_login_rejects_untrusted_target_link_uri(client: TestClient) -> None:
    response = client.get(
        "/api/lti/login",
        params={
            "iss": "https://sandbox.brightspace.com",
            "login_hint": "hint",
            "target_link_uri": "https://attacker.example/steal",
            "client_id": "client-123",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_target_link_uri"


def test_instructor_launch_succeeds_with_context(client: TestClient, keypair: tuple[str, str]) -> None:
    platform_private_key, _ = keypair
    state, nonce = _launch_params(client)
    token = _make_token(
        platform_private_key,
        nonce,
        ["http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"],
    )

    response = client.post("/api/lti/launch", data={"state": state, "id_token": token})

    assert response.status_code == 200
    launch_context = response.json()["launch_context"]
    assert launch_context == {
        "user_id": "user-42",
        "org_unit_id": "6606",
        "roles": ["http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"],
        "resource_link_id": "resource-1",
    }


def test_student_launch_is_forbidden(client: TestClient, keypair: tuple[str, str]) -> None:
    platform_private_key, _ = keypair
    state, nonce = _launch_params(client)
    token = _make_token(
        platform_private_key,
        nonce,
        ["http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"],
    )

    response = client.post("/api/lti/launch", data={"state": state, "id_token": token})

    assert response.status_code == 403
    assert response.json()["detail"] == "forbidden_role"


def test_replayed_nonce_fails(client: TestClient, keypair: tuple[str, str]) -> None:
    platform_private_key, _ = keypair
    state, nonce = _launch_params(client)
    token = _make_token(
        platform_private_key,
        nonce,
        ["http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"],
    )

    first = client.post("/api/lti/launch", data={"state": state, "id_token": token})
    second = client.post("/api/lti/launch", data={"state": state, "id_token": token})

    assert first.status_code == 200
    assert second.status_code == 401
    assert second.json()["detail"] == "invalid_or_replayed_nonce"


def test_invalid_signature_fails(client: TestClient, keypair: tuple[str, str]) -> None:
    state, nonce = _launch_params(client)
    wrong_private_key, _ = _generate_rsa_keypair()
    wrong_token = _make_token(
        wrong_private_key,
        nonce,
        ["http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"],
    )

    response = client.post("/api/lti/launch", data={"state": state, "id_token": wrong_token})

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_id_token"


def _generate_rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem
