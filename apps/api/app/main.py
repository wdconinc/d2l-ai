from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Annotated, cast

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

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
from app.usage_metering import HardBudgetCapExceeded, UsageMeter

configure_logging(settings.log_level)
http_bearer = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_telemetry(_app, settings)
    yield


def _require_bearer_token(
    secret_env_var: str,
    credentials: HTTPAuthorizationCredentials | None,
) -> None:
    expected_token = os.getenv(secret_env_var)
    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail="errors.service.unavailable",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="errors.auth.bearer_required")
    if credentials.credentials != expected_token:
        raise HTTPException(status_code=403, detail="errors.auth.invalid_token")


def require_admin_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
) -> None:
    _require_bearer_token("D2L_AI_ADMIN_API_TOKEN", credentials)


def require_llm_call_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
) -> None:
    _require_bearer_token("D2L_AI_LLM_CALL_TOKEN", credentials)


def get_meter(request: Request) -> UsageMeter:
    return cast(UsageMeter, request.app.state.meter)


class BudgetCapsPayload(BaseModel):
    soft_limit_usd: float | None = Field(default=None, ge=0)
    hard_limit_usd: float | None = Field(default=None, ge=0)


class MeteredCallPayload(BaseModel):
    workflow_id: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)


class BudgetCapsResponse(BaseModel):
    tenant_id: str
    soft_limit_usd: float | None = None
    hard_limit_usd: float | None = None


class WorkflowUsageResponse(BaseModel):
    call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class TenantUsageResponse(BaseModel):
    tenant_id: str
    call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    workflows: dict[str, WorkflowUsageResponse]


class MeteredCallResponse(BaseModel):
    tenant_id: str
    warning: str | None = None
    usage: TenantUsageResponse


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
    app.state.meter = UsageMeter()
    app.include_router(lti_router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/lti/deep-linking/response")
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

    @app.post("/admin/tenants/{tenant_id}/budget-caps")
    def set_budget_caps(
        tenant_id: str,
        payload: BudgetCapsPayload,
        _: Annotated[None, Depends(require_admin_token)],
        meter: Annotated[UsageMeter, Depends(get_meter)],
    ) -> BudgetCapsResponse:
        try:
            caps = meter.set_budget_caps(
                tenant_id,
                soft_limit_usd=payload.soft_limit_usd,
                hard_limit_usd=payload.hard_limit_usd,
            )
        except ValueError as exc:
            error_map = {
                "soft_limit_usd must be >= 0": "errors.budget.soft_limit_negative",
                "hard_limit_usd must be >= 0": "errors.budget.hard_limit_negative",
                "soft_limit_usd cannot exceed hard_limit_usd": "errors.budget.soft_exceeds_hard",
            }
            raise HTTPException(
                status_code=400,
                detail=error_map.get(str(exc), "errors.budget.invalid_configuration"),
            ) from exc
        return BudgetCapsResponse(
            tenant_id=tenant_id,
            soft_limit_usd=caps.soft_limit_usd,
            hard_limit_usd=caps.hard_limit_usd,
        )

    @app.get("/admin/tenants/{tenant_id}/budget-caps")
    def get_budget_caps(
        tenant_id: str,
        _: Annotated[None, Depends(require_admin_token)],
        meter: Annotated[UsageMeter, Depends(get_meter)],
    ) -> BudgetCapsResponse:
        caps = meter.get_budget_caps(tenant_id)
        return BudgetCapsResponse(
            tenant_id=tenant_id,
            soft_limit_usd=caps.soft_limit_usd,
            hard_limit_usd=caps.hard_limit_usd,
        )

    @app.get("/admin/tenants/{tenant_id}/usage")
    def get_tenant_usage(
        tenant_id: str,
        _: Annotated[None, Depends(require_admin_token)],
        meter: Annotated[UsageMeter, Depends(get_meter)],
    ) -> TenantUsageResponse:
        usage = meter.get_tenant_usage(tenant_id)
        return TenantUsageResponse(
            tenant_id=tenant_id,
            call_count=usage.call_count,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            estimated_cost_usd=usage.estimated_cost_usd,
            workflows={
                workflow_id: WorkflowUsageResponse(
                    call_count=workflow.call_count,
                    input_tokens=workflow.input_tokens,
                    output_tokens=workflow.output_tokens,
                    total_tokens=workflow.total_tokens,
                    estimated_cost_usd=workflow.estimated_cost_usd,
                )
                for workflow_id, workflow in usage.workflows.items()
            },
        )

    @app.post("/tenants/{tenant_id}/llm/calls")
    def record_llm_call(
        tenant_id: str,
        payload: MeteredCallPayload,
        _: Annotated[None, Depends(require_llm_call_token)],
        meter: Annotated[UsageMeter, Depends(get_meter)],
    ) -> MeteredCallResponse:
        try:
            decision = meter.record_llm_call(
                tenant_id=tenant_id,
                workflow_id=payload.workflow_id,
                input_tokens=payload.input_tokens,
                output_tokens=payload.output_tokens,
                estimated_cost_usd=payload.estimated_cost_usd,
            )
        except HardBudgetCapExceeded as exc:
            raise HTTPException(status_code=403, detail=exc.args[0]) from exc

        usage = meter.get_tenant_usage(tenant_id)
        return MeteredCallResponse(
            tenant_id=tenant_id,
            warning=decision.warning,
            usage=TenantUsageResponse(
                tenant_id=tenant_id,
                call_count=usage.call_count,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                estimated_cost_usd=usage.estimated_cost_usd,
                workflows={
                    workflow_id: WorkflowUsageResponse(
                        call_count=workflow.call_count,
                        input_tokens=workflow.input_tokens,
                        output_tokens=workflow.output_tokens,
                        total_tokens=workflow.total_tokens,
                        estimated_cost_usd=workflow.estimated_cost_usd,
                    )
                    for workflow_id, workflow in usage.workflows.items()
                },
            ),
        )

    env_client: BrightspaceOAuthClient | None = None
    if _oauth_env_is_configured():
        env_client = _build_default_oauth_client()
    brightspace_client = client or env_client
    if brightspace_client is None:
        return app

    @app.get("/brightspace/oauth/authorize-url")
    def get_authorize_url(state: str = Query(min_length=1, max_length=512)) -> dict[str, str]:
        return {"authorization_url": brightspace_client.build_authorization_url(state)}

    @app.get("/brightspace/oauth/callback")
    def oauth_callback(
        code: str = Query(min_length=1, max_length=2048),
        state: str = Query(min_length=1, max_length=512),
        token_owner: str = Query(default="service", max_length=64),
    ) -> dict[str, str]:
        brightspace_client.exchange_code_for_tokens(code=code, token_owner=token_owner)
        return {"status": "ok", "state": state}

    return app


app = create_app()
