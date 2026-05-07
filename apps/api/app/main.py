from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, Query

from app.brightspace.oauth_client import BrightspaceOAuthClient, BrightspaceOAuthConfig
from app.brightspace.token_store import EncryptedRefreshTokenStore
from app.logging import configure_logging
from app.settings import settings
from app.telemetry import configure_telemetry

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_telemetry(_app, settings)
    yield


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

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready"}

    brightspace_client = client or (_build_default_oauth_client() if _oauth_env_is_configured() else None)
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
