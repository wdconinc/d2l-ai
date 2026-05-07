from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import Lock


@dataclass(slots=True)
class BudgetCaps:
    soft_limit_usd: float | None = None
    hard_limit_usd: float | None = None


@dataclass(slots=True)
class WorkflowUsage:
    call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass(slots=True)
class TenantUsage:
    call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    workflows: dict[str, WorkflowUsage] = field(default_factory=dict)


@dataclass(slots=True)
class UsageDecision:
    warning: str | None = None


class HardBudgetCapExceeded(Exception):
    """Raised when a tenant hard budget cap would be exceeded."""


class UsageMeter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._budgets: dict[str, BudgetCaps] = {}
        self._usage: dict[str, TenantUsage] = {}

    def set_budget_caps(
        self,
        tenant_id: str,
        *,
        soft_limit_usd: float | None,
        hard_limit_usd: float | None,
    ) -> BudgetCaps:
        if soft_limit_usd is not None and soft_limit_usd < 0:
            raise ValueError("soft_limit_usd must be >= 0")
        if hard_limit_usd is not None and hard_limit_usd < 0:
            raise ValueError("hard_limit_usd must be >= 0")
        if (
            soft_limit_usd is not None
            and hard_limit_usd is not None
            and soft_limit_usd > hard_limit_usd
        ):
            raise ValueError("soft_limit_usd cannot exceed hard_limit_usd")

        caps = BudgetCaps(soft_limit_usd=soft_limit_usd, hard_limit_usd=hard_limit_usd)
        with self._lock:
            self._budgets[tenant_id] = caps
        return caps

    def get_budget_caps(self, tenant_id: str) -> BudgetCaps:
        with self._lock:
            caps = self._budgets.get(tenant_id, BudgetCaps())
            return BudgetCaps(
                soft_limit_usd=caps.soft_limit_usd,
                hard_limit_usd=caps.hard_limit_usd,
            )

    def get_tenant_usage(self, tenant_id: str) -> TenantUsage:
        with self._lock:
            usage = self._usage.get(tenant_id, TenantUsage())
            return deepcopy(usage)

    def record_llm_call(
        self,
        *,
        tenant_id: str,
        workflow_id: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
    ) -> UsageDecision:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token counts must be >= 0")
        if estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be >= 0")

        with self._lock:
            caps = self._budgets.get(tenant_id, BudgetCaps())
            tenant_usage = self._usage.setdefault(tenant_id, TenantUsage())
            projected_cost = tenant_usage.estimated_cost_usd + estimated_cost_usd

            if caps.hard_limit_usd is not None and projected_cost > caps.hard_limit_usd:
                raise HardBudgetCapExceeded(
                    "Budget limit reached for this tenant. Please contact your administrator "
                    "to increase the budget cap before making new AI requests."
                )

            tenant_usage.call_count += 1
            tenant_usage.input_tokens += input_tokens
            tenant_usage.output_tokens += output_tokens
            tenant_usage.total_tokens += input_tokens + output_tokens
            tenant_usage.estimated_cost_usd = projected_cost

            workflow_usage = tenant_usage.workflows.setdefault(workflow_id, WorkflowUsage())
            workflow_usage.call_count += 1
            workflow_usage.input_tokens += input_tokens
            workflow_usage.output_tokens += output_tokens
            workflow_usage.total_tokens += input_tokens + output_tokens
            workflow_usage.estimated_cost_usd += estimated_cost_usd

            warning: str | None = None
            if (
                caps.soft_limit_usd is not None
                and tenant_usage.estimated_cost_usd >= caps.soft_limit_usd
            ):
                warning = (
                    "Tenant budget soft cap has been reached. Requests continue for now, "
                    "but the hard cap may block further AI calls."
                )

            return UsageDecision(warning=warning)
