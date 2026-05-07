from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .usage_metering import HardBudgetCapExceeded, UsageMeter

app = FastAPI(title="d2l-ai API")
app.state.meter = UsageMeter()
bearer_scheme = HTTPBearer(auto_error=False)


def get_meter() -> UsageMeter:
    return app.state.meter


def _require_bearer_token(
    secret_env_var: str,
    credentials: HTTPAuthorizationCredentials | None,
) -> None:
    expected_token = os.getenv(secret_env_var)
    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail=f"Server misconfiguration: {secret_env_var} is not set.",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token authentication is required.")
    if credentials.credentials != expected_token:
        raise HTTPException(status_code=403, detail="Invalid authentication token.")


def require_admin_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    _require_bearer_token("D2L_AI_ADMIN_API_TOKEN", credentials)


def require_llm_call_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    _require_bearer_token("D2L_AI_LLM_CALL_TOKEN", credentials)


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


@app.post("/admin/tenants/{tenant_id}/budget-caps")
def set_budget_caps(
    tenant_id: str,
    payload: BudgetCapsPayload,
    _: None = Depends(require_admin_token),
    meter: UsageMeter = Depends(get_meter),
) -> BudgetCapsResponse:
    try:
        caps = meter.set_budget_caps(
            tenant_id,
            soft_limit_usd=payload.soft_limit_usd,
            hard_limit_usd=payload.hard_limit_usd,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BudgetCapsResponse(
        tenant_id=tenant_id,
        soft_limit_usd=caps.soft_limit_usd,
        hard_limit_usd=caps.hard_limit_usd,
    )


@app.get("/admin/tenants/{tenant_id}/budget-caps")
def get_budget_caps(
    tenant_id: str,
    _: None = Depends(require_admin_token),
    meter: UsageMeter = Depends(get_meter),
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
    _: None = Depends(require_admin_token),
    meter: UsageMeter = Depends(get_meter),
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
    _: None = Depends(require_llm_call_token),
    meter: UsageMeter = Depends(get_meter),
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
        raise HTTPException(status_code=403, detail=str(exc)) from exc

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
