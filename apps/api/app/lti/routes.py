from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from pylti1p3.tool_config import ToolConfDict

from app.lti.config import LTISettings, get_lti_settings, get_tool_conf
from app.lti.state import LTIStateNonceStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lti", tags=["lti"])
_oidc_store = LTIStateNonceStore(ttl_seconds=300)


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
    context = claims.get("https://purl.imsglobal.org/spec/lti/claim/context", {})
    custom = claims.get("https://purl.imsglobal.org/spec/lti/claim/custom", {})
    return custom.get("org_unit_id") or context.get("id")


def get_oidc_store() -> LTIStateNonceStore:
    return _oidc_store


def _validate_login_hint(value: str, field_name: str) -> str:
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid_auth_login_url")
    return urlunsplit((auth_parts.scheme, auth_parts.netloc, auth_parts.path, "", ""))


@router.get("/jwks")
def jwks(tool_conf: ToolConfDict = Depends(get_tool_conf)) -> dict[str, list[dict[str, Any]]]:
    settings = get_lti_settings()
    jwks_payload = tool_conf.get_jwks(settings.issuer, settings.client_id)
    for key in jwks_payload.get("keys", []):
        key["kid"] = settings.key_id
    return jwks_payload


@router.get("/login")
def oidc_login(
    iss: str,
    login_hint: str,
    target_link_uri: str,
    lti_message_hint: str | None = None,
    client_id: str | None = None,
    settings: LTISettings = Depends(get_lti_settings),
    oidc_store: LTIStateNonceStore = Depends(get_oidc_store),
) -> RedirectResponse:
    if iss != settings.issuer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_issuer")

    if client_id and client_id != settings.client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_client")

    if target_link_uri != settings.launch_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_target_link_uri")

    state, nonce = oidc_store.issue()
    safe_login_hint = _validate_login_hint(login_hint, "login_hint")
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
        query["lti_message_hint"] = _validate_login_hint(lti_message_hint, "lti_message_hint")

    trusted_auth_url = _trusted_auth_login_url(settings)
    return RedirectResponse(url=f"{trusted_auth_url}?{urlencode(query)}")


@router.post("/launch")
def launch(
    state: str = Form(...),
    id_token: str = Form(...),
    settings: LTISettings = Depends(get_lti_settings),
    tool_conf: ToolConfDict = Depends(get_tool_conf),
    oidc_store: LTIStateNonceStore = Depends(get_oidc_store),
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_id_token") from exc

    token_deployment_id = claims.get("https://purl.imsglobal.org/spec/lti/claim/deployment_id")
    if not token_deployment_id or not tool_conf.find_deployment_by_params(
        settings.issuer, token_deployment_id, settings.client_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid_deployment")

    nonce = claims.get("nonce")
    if not nonce:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_or_replayed_nonce")
    if not oidc_store.consume(state, nonce):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_or_replayed_nonce")

    roles = claims.get("https://purl.imsglobal.org/spec/lti/claim/roles", [])
    if not _is_instructor(roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_role")

    launch_context = {
        "user_id": claims.get("sub"),
        "org_unit_id": _extract_org_unit_id(claims),
        "roles": roles,
        "resource_link_id": claims.get("https://purl.imsglobal.org/spec/lti/claim/resource_link", {}).get("id"),
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


def configure_oidc_store(settings: LTISettings) -> None:
    global _oidc_store
    _oidc_store = LTIStateNonceStore(ttl_seconds=settings.state_ttl_seconds)
