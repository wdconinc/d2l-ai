from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .usage_metering import HardBudgetCapExceeded, UsageMeter

app = FastAPI(title="d2l-ai API")
meter = UsageMeter()


class BudgetCapsPayload(BaseModel):
    soft_limit_usd: float | None = Field(default=None, ge=0)
    hard_limit_usd: float | None = Field(default=None, ge=0)


class MeteredCallPayload(BaseModel):
    tenant_id: str
    workflow_id: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)


@app.post("/admin/tenants/{tenant_id}/budget-caps")
def set_budget_caps(tenant_id: str, payload: BudgetCapsPayload) -> dict[str, float | None]:
    try:
        caps = meter.set_budget_caps(
            tenant_id,
            soft_limit_usd=payload.soft_limit_usd,
            hard_limit_usd=payload.hard_limit_usd,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "tenant_id": tenant_id,
        "soft_limit_usd": caps.soft_limit_usd,
        "hard_limit_usd": caps.hard_limit_usd,
    }


@app.get("/admin/tenants/{tenant_id}/budget-caps")
def get_budget_caps(tenant_id: str) -> dict[str, float | None]:
    caps = meter.get_budget_caps(tenant_id)
    return {
        "tenant_id": tenant_id,
        "soft_limit_usd": caps.soft_limit_usd,
        "hard_limit_usd": caps.hard_limit_usd,
    }


@app.get("/admin/tenants/{tenant_id}/usage")
def get_tenant_usage(tenant_id: str) -> dict[str, object]:
    usage = meter.get_tenant_usage(tenant_id)
    return {
        "tenant_id": tenant_id,
        "call_count": usage.call_count,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "estimated_cost_usd": usage.estimated_cost_usd,
        "workflows": {
            workflow_id: {
                "call_count": workflow.call_count,
                "input_tokens": workflow.input_tokens,
                "output_tokens": workflow.output_tokens,
                "total_tokens": workflow.total_tokens,
                "estimated_cost_usd": workflow.estimated_cost_usd,
            }
            for workflow_id, workflow in usage.workflows.items()
        },
    }


@app.post("/llm/calls")
def record_llm_call(payload: MeteredCallPayload) -> dict[str, object]:
    try:
        decision = meter.record_llm_call(
            tenant_id=payload.tenant_id,
            workflow_id=payload.workflow_id,
            input_tokens=payload.input_tokens,
            output_tokens=payload.output_tokens,
            estimated_cost_usd=payload.estimated_cost_usd,
        )
    except HardBudgetCapExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    usage = meter.get_tenant_usage(payload.tenant_id)
    return {
        "tenant_id": payload.tenant_id,
        "warning": decision.warning,
        "usage": {
            "call_count": usage.call_count,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
            "estimated_cost_usd": usage.estimated_cost_usd,
        },
    }
