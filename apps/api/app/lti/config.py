from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from pylti1p3.tool_config import ToolConfDict


@dataclass(frozen=True)
class LTISettings:
    issuer: str
    client_id: str
    deployment_id: str
    auth_login_url: str
    auth_token_url: str
    launch_url: str
    platform_public_key_pem: str
    tool_private_key_pem: str
    tool_public_key_pem: str
    key_id: str
    state_ttl_seconds: int = 300
    state_db_path: str = ""


@lru_cache(maxsize=1)
def get_lti_settings() -> LTISettings:
    issuer = os.getenv("LTI_ISSUER")
    client_id = os.getenv("LTI_CLIENT_ID")
    deployment_id = os.getenv("LTI_DEPLOYMENT_ID")
    auth_login_url = os.getenv("LTI_AUTH_LOGIN_URL")
    auth_token_url = os.getenv("LTI_AUTH_TOKEN_URL")
    launch_url = os.getenv("LTI_LAUNCH_URL")
    platform_public_key_pem = os.getenv("LTI_PLATFORM_PUBLIC_KEY_PEM")
    tool_private_key_pem = os.getenv("LTI_TOOL_PRIVATE_KEY_PEM")
    tool_public_key_pem = os.getenv("LTI_TOOL_PUBLIC_KEY_PEM")
    key_id = os.getenv("LTI_TOOL_KEY_ID", "um-ai-tool-key")
    state_ttl_seconds = int(os.getenv("LTI_STATE_TTL_SECONDS", "300"))
    state_db_path = os.getenv("LTI_STATE_DB_PATH")
    if not issuer or not client_id or not deployment_id or not auth_login_url or not auth_token_url or not launch_url:
        raise RuntimeError(
            "LTI issuer/client/deployment/login/token/launch URLs must be configured via environment variables."
        )
    if not state_db_path:
        raise RuntimeError("LTI_STATE_DB_PATH must be configured.")
    if not platform_public_key_pem or not tool_private_key_pem or not tool_public_key_pem:
        raise RuntimeError(
            "LTI keys must be configured via LTI_PLATFORM_PUBLIC_KEY_PEM, "
            "LTI_TOOL_PRIVATE_KEY_PEM, and LTI_TOOL_PUBLIC_KEY_PEM."
        )

    return LTISettings(
        issuer=issuer,
        client_id=client_id,
        deployment_id=deployment_id,
        auth_login_url=auth_login_url,
        auth_token_url=auth_token_url,
        launch_url=launch_url,
        platform_public_key_pem=platform_public_key_pem,
        tool_private_key_pem=tool_private_key_pem,
        tool_public_key_pem=tool_public_key_pem,
        key_id=key_id,
        state_ttl_seconds=state_ttl_seconds,
        state_db_path=state_db_path,
    )


@lru_cache(maxsize=1)
def get_tool_conf() -> ToolConfDict:
    settings = get_lti_settings()
    tool_conf = ToolConfDict(
        {
            settings.issuer: {
                "client_id": settings.client_id,
                "auth_login_url": settings.auth_login_url,
                "auth_token_url": settings.auth_token_url,
                "deployment_ids": [settings.deployment_id],
            }
        }
    )
    tool_conf.set_public_key(settings.issuer, settings.tool_public_key_pem, settings.client_id)
    tool_conf.set_private_key(settings.issuer, settings.tool_private_key_pem, settings.client_id)
    return tool_conf
