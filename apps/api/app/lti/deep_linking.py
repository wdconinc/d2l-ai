from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import jwt
from pydantic import BaseModel, Field, field_validator, model_validator

MESSAGE_TYPE_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/message_type"
VERSION_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/version"
DEPLOYMENT_ID_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
DEEP_LINKING_SETTINGS_CLAIM = "https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings"
CONTENT_ITEMS_CLAIM = "https://purl.imsglobal.org/spec/lti-dl/claim/content_items"
DATA_CLAIM = "https://purl.imsglobal.org/spec/lti-dl/claim/data"


class DeepLinkingRequestError(ValueError):
    """Raised when an incoming launch payload is not a valid deep-linking request."""


class ContentItemType(str, Enum):
    HTML = "html"
    LINK = "link"


class Provenance(BaseModel):
    model: str = "pending"
    prompt_hash: str = "pending"
    version: str = "v0"
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ContentSelection(BaseModel):
    item_type: ContentItemType
    title: str
    text: str | None = None
    html: str | None = None
    url: str | None = None
    provenance: Provenance = Field(default_factory=Provenance)

    @model_validator(mode="after")
    def validate_payload(self) -> "ContentSelection":
        if self.item_type == ContentItemType.HTML and not self.html:
            raise ValueError("html payload is required for html content items")
        if self.item_type == ContentItemType.LINK and not self.url:
            raise ValueError("url is required for link content items")
        return self


class DeepLinkingResponseRequest(BaseModel):
    launch_claims: dict[str, Any]
    selection: ContentSelection

    @field_validator("launch_claims")
    @classmethod
    def launch_claims_must_not_be_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("launch_claims are required")
        return value


@dataclass(frozen=True)
class DeepLinkingConfig:
    issuer: str
    private_key_pem: str
    key_id: str
    algorithm: str = "RS256"


class DeepLinkingResponseBuilder:
    def __init__(self, config: DeepLinkingConfig) -> None:
        self._config = config

    @staticmethod
    def validate_deep_linking_launch(launch_claims: dict[str, Any]) -> dict[str, Any]:
        if launch_claims.get(MESSAGE_TYPE_CLAIM) != "LtiDeepLinkingRequest":
            raise DeepLinkingRequestError("launch is not an LtiDeepLinkingRequest")

        settings = launch_claims.get(DEEP_LINKING_SETTINGS_CLAIM)
        if not isinstance(settings, dict):
            raise DeepLinkingRequestError("missing deep_linking_settings claim")

        deep_link_return_url = settings.get("deep_link_return_url")
        if not deep_link_return_url:
            raise DeepLinkingRequestError("missing deep_link_return_url in deep_linking_settings")

        return settings

    @staticmethod
    def make_content_item(selection: ContentSelection) -> dict[str, Any]:
        item: dict[str, Any] = {
            "type": selection.item_type.value,
            "title": selection.title,
            "custom": {"provenance": selection.provenance.model_dump()},
        }
        if selection.text:
            item["text"] = selection.text

        if selection.item_type == ContentItemType.HTML:
            item["html"] = selection.html
        else:
            item["url"] = selection.url

        return item

    def build_signed_response_jwt(
        self,
        launch_claims: dict[str, Any],
        items: list[dict[str, Any]],
    ) -> tuple[str, str]:
        settings = self.validate_deep_linking_launch(launch_claims)
        return_url = settings["deep_link_return_url"]

        claims: dict[str, Any] = {
            "iss": self._config.issuer,
            "aud": launch_claims["iss"],
            MESSAGE_TYPE_CLAIM: "LtiDeepLinkingResponse",
            VERSION_CLAIM: "1.3.0",
            CONTENT_ITEMS_CLAIM: items,
            "iat": int(datetime.now(UTC).timestamp()),
            "nonce": str(uuid4()),
        }
        if DEPLOYMENT_ID_CLAIM in launch_claims:
            claims[DEPLOYMENT_ID_CLAIM] = launch_claims[DEPLOYMENT_ID_CLAIM]
        if "data" in settings:
            claims[DATA_CLAIM] = settings["data"]

        token = jwt.encode(
            payload=claims,
            key=self._config.private_key_pem,
            algorithm=self._config.algorithm,
            headers={"kid": self._config.key_id, "typ": "JWT"},
        )
        return return_url, token


def build_static_html_topic_selection() -> ContentSelection:
    return ContentSelection(
        item_type=ContentItemType.HTML,
        title="Sample AI Topic (Draft)",
        text="Static sample content returned from deep-linking flow.",
        html=(
            "<!-- generated-by: UM-AI-Tool v0, model=pending, prompt-hash=pending -->"
            "<h2>Sample AI Topic (Draft)</h2>"
            "<p>This is a static deep-linking sample. Review before insertion.</p>"
        ),
    )
