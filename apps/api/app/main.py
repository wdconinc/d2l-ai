from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .usage_metering import HardBudgetCapExceeded, UsageMeter

app = FastAPI(title="d2l-ai API")
app.state.meter = UsageMeter()


def get_meter() -> UsageMeter:
    return app.state.meter


def require_admin(admin_subject: str | None = Header(default=None, alias="X-Admin-Subject")) -> str:
    if not admin_subject:
        raise HTTPException(status_code=401, detail="Admin authentication is required.")
    return admin_subject


def require_tenant_context(tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")) -> str:
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing tenant context header: X-Tenant-Id")
    return tenant_id


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
    usage: WorkflowUsageResponse


@app.post("/admin/tenants/{tenant_id}/budget-caps")
def set_budget_caps(
    tenant_id: str,
    payload: BudgetCapsPayload,
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
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
    _: str = Depends(require_admin),
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


@app.post("/llm/calls")
def record_llm_call(
    payload: MeteredCallPayload,
    tenant_id: str = Depends(require_tenant_context),
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
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    usage = meter.get_tenant_usage(tenant_id)
    return MeteredCallResponse(
        tenant_id=tenant_id,
        warning=decision.warning,
        usage=WorkflowUsageResponse(
            call_count=usage.call_count,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            estimated_cost_usd=usage.estimated_cost_usd,
        ),
    )
