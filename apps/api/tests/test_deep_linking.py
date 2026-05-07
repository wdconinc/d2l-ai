from __future__ import annotations

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.lti.deep_linking import (
    CONTENT_ITEMS_CLAIM,
    DATA_CLAIM,
    MESSAGE_TYPE_CLAIM,
    VERSION_CLAIM,
    ContentItemType,
    ContentSelection,
    DeepLinkingConfig,
    DeepLinkingRequestError,
    DeepLinkingResponseBuilder,
    build_static_html_topic_selection,
)
from app.main import app, get_deep_linking_config


@pytest.fixture()
def keys() -> dict[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return {"private": private_pem, "public": public_pem}


@pytest.fixture()
def launch_claims() -> dict[str, object]:
    return {
        "iss": "https://brightspace.example",
        MESSAGE_TYPE_CLAIM: "LtiDeepLinkingRequest",
        VERSION_CLAIM: "1.3.0",
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id": "deployment-1",
        "https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings": {
            "deep_link_return_url": "https://brightspace.example/deep-link-return",
            "data": "opaque-data",
        },
    }


def _builder(keys: dict[str, str]) -> DeepLinkingResponseBuilder:
    return DeepLinkingResponseBuilder(
        DeepLinkingConfig(
            issuer="urn:umanitoba:d2l-ai",
            private_key_pem=keys["private"],
            key_id="test-key",
        )
    )


def test_build_signed_response_jwt_shape(
    launch_claims: dict[str, object], keys: dict[str, str]
) -> None:
    builder = _builder(keys)
    selection = ContentSelection(
        item_type=ContentItemType.HTML,
        title="Static Topic",
        text="Sample",
        html="<p>topic</p>",
    )

    return_url, token = builder.build_signed_response_jwt(
        launch_claims=launch_claims,
        items=[builder.make_content_item(selection)],
    )

    decoded = jwt.decode(
        token,
        keys["public"],
        algorithms=["RS256"],
        audience="https://brightspace.example",
    )

    assert return_url == "https://brightspace.example/deep-link-return"
    assert decoded[MESSAGE_TYPE_CLAIM] == "LtiDeepLinkingResponse"
    assert decoded[VERSION_CLAIM] == "1.3.0"
    assert decoded[DATA_CLAIM] == "opaque-data"
    assert decoded[CONTENT_ITEMS_CLAIM][0]["title"] == "Static Topic"
    assert decoded[CONTENT_ITEMS_CLAIM][0]["html"] == "<p>topic</p>"
    assert "provenance" in decoded[CONTENT_ITEMS_CLAIM][0]["custom"]


def test_invalid_deep_linking_launch_rejected() -> None:
    with pytest.raises(DeepLinkingRequestError):
        DeepLinkingResponseBuilder.validate_deep_linking_launch(
            {
                "iss": "https://brightspace.example",
                MESSAGE_TYPE_CLAIM: "LtiResourceLinkRequest",
            }
        )


def test_static_html_topic_sample_contains_provenance_comment() -> None:
    selection = build_static_html_topic_selection()

    assert "generated-by: UM-AI-Tool" in selection.html
    assert selection.provenance.model == "pending"


def test_endpoint_rejects_invalid_request(
    keys: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("D2L_AI_LTI_ISSUER", "urn:umanitoba:d2l-ai")
    monkeypatch.setenv("D2L_AI_LTI_PRIVATE_KEY", keys["private"])
    monkeypatch.setenv("D2L_AI_LTI_KEY_ID", "test-key")
    get_deep_linking_config.cache_clear()

    client = TestClient(app)
    response = client.post(
        "/lti/deep-linking/response",
        json={
            "launch_claims": {
                "iss": "https://brightspace.example",
                MESSAGE_TYPE_CLAIM: "LtiResourceLinkRequest",
                "https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings": {
                    "deep_link_return_url": "https://brightspace.example/deep-link-return"
                },
            },
            "selection": {
                "item_type": "link",
                "title": "resource",
                "url": "https://example.ca/resource",
            },
        },
    )

    assert response.status_code == 400
