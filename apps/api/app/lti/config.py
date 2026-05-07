from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@dataclass(frozen=True)
class LTISettings:
    issuer: str
    client_id: str
    deployment_id: str
    auth_login_url: str
    platform_public_key_pem: str
    tool_private_key_pem: str
    tool_public_key_pem: str
    key_id: str
    state_ttl_seconds: int = 300


def _generate_tool_keypair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


_GENERATED_TOOL_PRIVATE, _GENERATED_TOOL_PUBLIC = _generate_tool_keypair()


@lru_cache(maxsize=1)
def get_lti_settings() -> LTISettings:
    issuer = os.getenv("LTI_ISSUER", "https://sandbox.brightspace.example")
    client_id = os.getenv("LTI_CLIENT_ID", "brightspace-client-id")
    deployment_id = os.getenv("LTI_DEPLOYMENT_ID", "brightspace-deployment-id")
    auth_login_url = os.getenv(
        "LTI_AUTH_LOGIN_URL",
        "https://sandbox.brightspace.example/d2l/lti/auth",
    )
    platform_public_key_pem = os.getenv("LTI_PLATFORM_PUBLIC_KEY_PEM", _GENERATED_TOOL_PUBLIC)
    tool_private_key_pem = os.getenv("LTI_TOOL_PRIVATE_KEY_PEM", _GENERATED_TOOL_PRIVATE)
    tool_public_key_pem = os.getenv("LTI_TOOL_PUBLIC_KEY_PEM", _GENERATED_TOOL_PUBLIC)
    key_id = os.getenv("LTI_TOOL_KEY_ID", "um-ai-tool-key")
    state_ttl_seconds = int(os.getenv("LTI_STATE_TTL_SECONDS", "300"))

    return LTISettings(
        issuer=issuer,
        client_id=client_id,
        deployment_id=deployment_id,
        auth_login_url=auth_login_url,
        platform_public_key_pem=platform_public_key_pem,
        tool_private_key_pem=tool_private_key_pem,
        tool_public_key_pem=tool_public_key_pem,
        key_id=key_id,
        state_ttl_seconds=state_ttl_seconds,
    )
