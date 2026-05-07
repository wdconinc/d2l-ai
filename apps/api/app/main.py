from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException

from app.lti.deep_linking import (
    DeepLinkingConfig,
    DeepLinkingRequestError,
    DeepLinkingResponseBuilder,
    DeepLinkingResponseRequest,
)
from app.logging import configure_logging
from app.settings import settings
from app.telemetry import configure_telemetry

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_telemetry(_app, settings)
    yield


app = FastAPI(title="d2l-ai API", version="0.1.0", lifespan=lifespan)


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
        raise RuntimeError(
            f"deep-linking signing configuration is missing: {', '.join(missing)}"
        )
    return DeepLinkingConfig(issuer=issuer, private_key_pem=private_key_pem, key_id=key_id)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/lti/deep-linking/response")
def build_deep_linking_response(
    request: DeepLinkingResponseRequest,
) -> dict[str, str]:
    try:
        builder = DeepLinkingResponseBuilder(get_deep_linking_config())
        content_item = builder.make_content_item(request.selection)
        return_url, token = builder.build_signed_response_jwt(request.launch_claims, [content_item])
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except DeepLinkingRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"deep_link_return_url": return_url, "JWT": token}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}
