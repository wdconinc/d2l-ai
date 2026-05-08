from __future__ import annotations

import logging
import re
from functools import lru_cache
from html import escape
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse
from pylti1p3.tool_config import ToolConfDict  # type: ignore[attr-defined]

from app.lti.config import LTISettings, get_lti_settings, get_tool_conf
from app.lti.state import LTIStateNonceStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lti", tags=["lti"])


def _is_instructor(roles: list[str]) -> bool:
    lowered = [role.lower() for role in roles]
    return any(
        marker in role
        for role in lowered
        for marker in (
            "#instructor",
            "#administrator",
            "urn:lti:instrole:ims/lis/instructor",
            "urn:lti:role:ims/lis/instructor",
        )
    )


def _extract_org_unit_id(claims: dict[str, Any]) -> str | None:
    context_claim = claims.get("https://purl.imsglobal.org/spec/lti/claim/context")
    custom_claim = claims.get("https://purl.imsglobal.org/spec/lti/claim/custom")
    context = context_claim if isinstance(context_claim, dict) else {}
    custom = custom_claim if isinstance(custom_claim, dict) else {}
    org_unit_id = custom.get("org_unit_id") or context.get("id")
    if org_unit_id is None:
        return None
    if isinstance(org_unit_id, (str, int)):
        return str(org_unit_id)
    return None


@lru_cache(maxsize=1)
def _build_oidc_store(ttl_seconds: int, state_db_path: str) -> LTIStateNonceStore:
    return LTIStateNonceStore(ttl_seconds=ttl_seconds, database_path=state_db_path)


def get_oidc_store(
    settings: LTISettings = Depends(get_lti_settings),  # noqa: B008
) -> LTIStateNonceStore:
    return _build_oidc_store(settings.state_ttl_seconds, settings.state_db_path)


def _validate_hint_parameter(value: str, field_name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,512}", value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid_{field_name}")
    return value


def _trusted_auth_login_url(settings: LTISettings) -> str:
    auth_parts = urlsplit(settings.auth_login_url)
    issuer_parts = urlsplit(settings.issuer)
    if (
        auth_parts.scheme != "https"
        or not auth_parts.netloc
        or auth_parts.netloc != issuer_parts.netloc
        or auth_parts.query
        or auth_parts.fragment
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid_auth_login_url"
        )
    return urlunsplit((auth_parts.scheme, auth_parts.netloc, auth_parts.path, "", ""))


@router.get("/jwks")
def jwks(
    tool_conf: ToolConfDict = Depends(get_tool_conf),  # noqa: B008
) -> dict[str, list[dict[str, Any]]]:
    settings = get_lti_settings()
    raw_jwks_payload = tool_conf.get_jwks(settings.issuer, settings.client_id)
    if not isinstance(raw_jwks_payload, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="invalid_jwks_payload_type",
        )
    keys = raw_jwks_payload.get("keys")
    if not isinstance(keys, list):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="invalid_jwks_keys_type",
        )
    jwks_payload: dict[str, list[dict[str, Any]]] = {"keys": []}
    for key in keys:
        if not isinstance(key, dict):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="invalid_jwks_key_entry_type",
            )
        typed_key = {**key, "kid": settings.key_id}
        jwks_payload["keys"].append(typed_key)
    return jwks_payload


@router.get("/login")
def oidc_login(
    iss: str,
    login_hint: str,
    target_link_uri: str,
    lti_message_hint: str | None = None,
    client_id: str | None = None,
    settings: LTISettings = Depends(get_lti_settings),  # noqa: B008
    oidc_store: LTIStateNonceStore = Depends(get_oidc_store),  # noqa: B008
) -> HTMLResponse:
    if iss != settings.issuer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_issuer")

    if client_id and client_id != settings.client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_client")

    if target_link_uri != settings.launch_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_target_link_uri"
        )

    state, nonce = oidc_store.issue()
    safe_login_hint = _validate_hint_parameter(login_hint, "login_hint")
    query = {
        "scope": "openid",
        "response_type": "id_token",
        "response_mode": "form_post",
        "prompt": "none",
        "client_id": settings.client_id,
        "redirect_uri": settings.launch_url,
        "login_hint": safe_login_hint,
        "state": state,
        "nonce": nonce,
    }
    if lti_message_hint:
        query["lti_message_hint"] = _validate_hint_parameter(lti_message_hint, "lti_message_hint")

    trusted_auth_url = _trusted_auth_login_url(settings)
    inputs = "\n".join(
        f'<input type="hidden" name="{escape(k)}" value="{escape(v)}" />' for k, v in query.items()
    )
    html = (
        "<!doctype html><html><body>"
        f'<form id="oidc-login" method="get" action="{escape(trusted_auth_url)}">{inputs}</form>'
        "<script>document.getElementById('oidc-login').submit();</script>"
        "</body></html>"
    )
    return HTMLResponse(content=html)


@router.post("/launch")
def launch(
    state: str = Form(...),
    id_token: str = Form(...),
    settings: LTISettings = Depends(get_lti_settings),  # noqa: B008
    tool_conf: ToolConfDict = Depends(get_tool_conf),  # noqa: B008
    oidc_store: LTIStateNonceStore = Depends(get_oidc_store),  # noqa: B008
) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            id_token,
            key=settings.platform_public_key_pem,
            algorithms=["RS256"],
            audience=settings.client_id,
            issuer=settings.issuer,
            options={"require": ["exp", "iat", "nonce", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_id_token"
        ) from exc

    token_deployment_id = claims.get("https://purl.imsglobal.org/spec/lti/claim/deployment_id")
    if not token_deployment_id or not tool_conf.find_deployment_by_params(
        settings.issuer, token_deployment_id, settings.client_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid_deployment")

    nonce = claims.get("nonce")
    if not nonce:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_or_replayed_nonce"
        )
    if not oidc_store.consume(state, nonce):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_or_replayed_nonce"
        )

    roles = claims.get("https://purl.imsglobal.org/spec/lti/claim/roles", [])
    if not _is_instructor(roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_role")

    launch_context = {
        "user_id": claims.get("sub"),
        "org_unit_id": _extract_org_unit_id(claims),
        "roles": roles,
        "resource_link_id": claims.get(
            "https://purl.imsglobal.org/spec/lti/claim/resource_link", {}
        ).get("id"),
    }
    correlation_id = str(uuid4())
    logger.info(
        "lti_launch_success",
        extra={"correlation_id": correlation_id, "launch_context": launch_context},
    )

    return {
        "status": "ok",
        "correlation_id": correlation_id,
        "launch_context": launch_context,
    }


def _reset_oidc_store_cache_for_tests() -> None:
    _build_oidc_store.cache_clear()
