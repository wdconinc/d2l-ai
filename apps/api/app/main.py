from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query

from app.brightspace.oauth_client import BrightspaceOAuthClient, BrightspaceOAuthConfig
from app.brightspace.token_store import EncryptedRefreshTokenStore
from app.logging import configure_logging
from app.lti.deep_linking import (
    DeepLinkingConfig,
    DeepLinkingRequestError,
    DeepLinkingResponseBuilder,
    DeepLinkingResponseRequest,
)
from app.lti.routes import router as lti_router
from app.settings import settings
from app.telemetry import configure_telemetry

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_telemetry(_app, settings)
    yield


@lru_cache(maxsize=1)
def get_deep_linking_config() -> DeepLinkingConfig:
    issuer = os.getenv("D2L_AI_LTI_ISSUER")
    private_key_pem = os.getenv("D2L_AI_LTI_PRIVATE_KEY")
    key_id = os.getenv("D2L_AI_LTI_KEY_ID")
    if not issuer or not private_key_pem or not key_id:
        missing = []
        if not issuer:
            missing.append("D2L_AI_LTI_ISSUER")
        if not private_key_pem:
            missing.append("D2L_AI_LTI_PRIVATE_KEY")
        if not key_id:
            missing.append("D2L_AI_LTI_KEY_ID")
        raise RuntimeError(f"deep-linking signing configuration is missing: {', '.join(missing)}")
    return DeepLinkingConfig(issuer=issuer, private_key_pem=private_key_pem, key_id=key_id)


@lru_cache(maxsize=1)
def _build_default_oauth_client() -> BrightspaceOAuthClient:
    config = BrightspaceOAuthConfig(
        tenant=os.environ["BRIGHTSPACE_TENANT"],
        client_id=os.environ["BRIGHTSPACE_CLIENT_ID"],
        client_secret=os.environ["BRIGHTSPACE_CLIENT_SECRET"],
        redirect_uri=os.environ["BRIGHTSPACE_REDIRECT_URI"],
        scopes=tuple(os.environ.get("BRIGHTSPACE_SCOPES", "core:*:*").split()),
        lp_version=os.environ.get("BRIGHTSPACE_LP_VERSION", "1.51"),
    )
    token_store = EncryptedRefreshTokenStore(
        db_path=os.environ["BRIGHTSPACE_TOKEN_DB_PATH"],
        encryption_key=os.environ["BRIGHTSPACE_TOKEN_ENCRYPTION_KEY"],
    )
    return BrightspaceOAuthClient(config=config, token_store=token_store)


def _oauth_env_is_configured() -> bool:
    required = {
        "BRIGHTSPACE_TENANT",
        "BRIGHTSPACE_CLIENT_ID",
        "BRIGHTSPACE_CLIENT_SECRET",
        "BRIGHTSPACE_REDIRECT_URI",
        "BRIGHTSPACE_TOKEN_DB_PATH",
        "BRIGHTSPACE_TOKEN_ENCRYPTION_KEY",
    }
    return required.issubset(os.environ)


def create_app(client: BrightspaceOAuthClient | None = None) -> FastAPI:
    app = FastAPI(title="d2l-ai API", version="0.1.0", lifespan=lifespan)
    app.include_router(lti_router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/lti/deep-linking/response")
    def build_deep_linking_response(request: DeepLinkingResponseRequest) -> dict[str, str]:
        try:
            builder = DeepLinkingResponseBuilder(get_deep_linking_config())
            content_item = builder.make_content_item(request.selection)
            return_url, token = builder.build_signed_response_jwt(
                request.launch_claims,
                [content_item],
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except DeepLinkingRequestError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {"deep_link_return_url": return_url, "JWT": token}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready"}

    env_client: BrightspaceOAuthClient | None = None
    if _oauth_env_is_configured():
        env_client = _build_default_oauth_client()
    brightspace_client = client or env_client
    if brightspace_client is None:
        return app

    @app.get("/brightspace/oauth/authorize-url")
    def get_authorize_url(state: str = Query(min_length=1)) -> dict[str, str]:
        return {"authorization_url": brightspace_client.build_authorization_url(state)}

    @app.get("/brightspace/oauth/callback")
    def oauth_callback(
        code: str = Query(min_length=1),
        state: str = Query(min_length=1),
        token_owner: str = Query(default="service"),
    ) -> dict[str, str]:
        brightspace_client.exchange_code_for_tokens(code=code, token_owner=token_owner)
        return {"status": "ok", "state": state}

    return app


app = create_app()
