from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode
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
    query = {
        "scope": "openid",
        "response_type": "id_token",
        "response_mode": "form_post",
        "prompt": "none",
        "client_id": settings.client_id,
        "redirect_uri": settings.launch_url,
        "login_hint": login_hint,
        "state": state,
        "nonce": nonce,
    }
    if lti_message_hint:
        query["lti_message_hint"] = lti_message_hint

    return RedirectResponse(url=f"{settings.auth_login_url}?{urlencode(query)}")


@router.post("/launch")
def launch(
    state: str = Form(...),
    id_token: str = Form(...),
    settings: LTISettings = Depends(get_lti_settings),
    tool_conf: ToolConfDict = Depends(get_tool_conf),
    oidc_store: LTIStateNonceStore = Depends(get_oidc_store),
) -> dict[str, Any]:
    if not oidc_store.has_state(state):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_or_replayed_state")

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
    if not nonce or not oidc_store.consume(state, nonce):
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
