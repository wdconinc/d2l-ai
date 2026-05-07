"""FastAPI app exposing Brightspace OAuth2 authorization/callback handlers."""

from __future__ import annotations

import os
from functools import lru_cache
from warnings import warn

from fastapi import FastAPI, Query

from .brightspace.oauth_client import BrightspaceOAuthClient, BrightspaceOAuthConfig
from .brightspace.token_store import EncryptedRefreshTokenStore


@lru_cache(maxsize=1)
def _build_default_client() -> BrightspaceOAuthClient:
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


def create_app(client: BrightspaceOAuthClient | None = None) -> FastAPI:
    brightspace_client = client or _build_default_client()
    app = FastAPI()

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


_required_env = {
    "BRIGHTSPACE_TENANT",
    "BRIGHTSPACE_CLIENT_ID",
    "BRIGHTSPACE_CLIENT_SECRET",
    "BRIGHTSPACE_REDIRECT_URI",
    "BRIGHTSPACE_TOKEN_DB_PATH",
    "BRIGHTSPACE_TOKEN_ENCRYPTION_KEY",
}
if _required_env.issubset(os.environ):
    app = create_app()
else:
    missing = ", ".join(sorted(_required_env.difference(os.environ)))
    warn(
        "Brightspace OAuth2 app not fully configured; "
        f"set BRIGHTSPACE_* environment variables (missing: {missing})",
        RuntimeWarning,
    )
    app = FastAPI()
