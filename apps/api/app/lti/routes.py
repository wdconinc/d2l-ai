from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from jwt.algorithms import RSAAlgorithm
from pylti1p3 import __version__ as pylti1p3_version

from app.lti.config import LTISettings, get_lti_settings
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
    context = claims.get("https://purl.imsglobal.org/spec/lti/claim/context", {})
    custom = claims.get("https://purl.imsglobal.org/spec/lti/claim/custom", {})
    return custom.get("org_unit_id") or context.get("id")


def _build_jwk(settings: LTISettings) -> dict[str, Any]:
    key = serialization_load_public_key(settings.tool_public_key_pem)
    jwk = json.loads(RSAAlgorithm.to_jwk(key))
    jwk.update({"kid": settings.key_id, "alg": "RS256", "use": "sig"})
    return jwk


def serialization_load_public_key(public_key_pem: str) -> Any:
    from cryptography.hazmat.primitives import serialization

    return serialization.load_pem_public_key(public_key_pem.encode("utf-8"))


@router.get("/jwks")
def jwks(settings: LTISettings = Depends(get_lti_settings)) -> dict[str, list[dict[str, Any]]]:
    return {"keys": [_build_jwk(settings)]}


@router.get("/login")
def oidc_login(
    iss: str,
    login_hint: str,
    target_link_uri: str,
    lti_message_hint: str | None = None,
    client_id: str | None = None,
    settings: LTISettings = Depends(get_lti_settings),
) -> RedirectResponse:
    if iss != settings.issuer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_issuer")

    if client_id and client_id != settings.client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_client")

    state, nonce = oidc_store.issue()
    query = {
        "scope": "openid",
        "response_type": "id_token",
        "response_mode": "form_post",
        "prompt": "none",
        "client_id": settings.client_id,
        "redirect_uri": target_link_uri,
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
    if token_deployment_id != settings.deployment_id:
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
        "lti_library": f"pylti1p3/{pylti1p3_version}",
    }


def configure_oidc_store(settings: LTISettings) -> None:
    global oidc_store
    oidc_store = LTIStateNonceStore(ttl_seconds=settings.state_ttl_seconds)


configure_oidc_store(get_lti_settings())
