import pytest

from app.usage_metering import HardBudgetCapExceeded, UsageMeter


def test_usage_recorded_for_every_call_and_workflow() -> None:
    meter = UsageMeter()

    meter.record_llm_call(
        tenant_id="tenant-1",
        workflow_id="u2_module_summary",
        input_tokens=10,
        output_tokens=5,
        estimated_cost_usd=0.01,
    )
    meter.record_llm_call(
        tenant_id="tenant-1",
        workflow_id="u3_quiz_generation",
        input_tokens=20,
        output_tokens=10,
        estimated_cost_usd=0.03,
    )

    usage = meter.get_tenant_usage("tenant-1")
    assert usage.call_count == 2
    assert usage.total_tokens == 45
    assert usage.estimated_cost_usd == pytest.approx(0.04)
    assert usage.workflows["u2_module_summary"].call_count == 1
    assert usage.workflows["u3_quiz_generation"].call_count == 1


def test_soft_cap_emits_warning() -> None:
    meter = UsageMeter()
    meter.set_budget_caps("tenant-1", soft_limit_usd=0.05, hard_limit_usd=0.10)

    decision = meter.record_llm_call(
        tenant_id="tenant-1",
        workflow_id="u2_module_summary",
        input_tokens=5,
        output_tokens=5,
        estimated_cost_usd=0.05,
    )

    assert decision.warning is not None


def test_hard_cap_blocks_new_calls() -> None:
    meter = UsageMeter()
    meter.set_budget_caps("tenant-1", soft_limit_usd=0.05, hard_limit_usd=0.06)

    meter.record_llm_call(
        tenant_id="tenant-1",
        workflow_id="u2_module_summary",
        input_tokens=10,
        output_tokens=10,
        estimated_cost_usd=0.05,
    )

    with pytest.raises(HardBudgetCapExceeded):
        meter.record_llm_call(
            tenant_id="tenant-1",
            workflow_id="u2_module_summary",
            input_tokens=1,
            output_tokens=1,
            estimated_cost_usd=0.02,
        )
