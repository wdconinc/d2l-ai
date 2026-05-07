import unittest

from app.usage_metering import HardBudgetCapExceeded, UsageMeter


class UsageMeterTests(unittest.TestCase):
    def test_usage_recorded_for_every_call_and_workflow(self) -> None:
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
        self.assertEqual(usage.call_count, 2)
        self.assertEqual(usage.total_tokens, 45)
        self.assertAlmostEqual(usage.estimated_cost_usd, 0.04)
        self.assertEqual(usage.workflows["u2_module_summary"].call_count, 1)
        self.assertEqual(usage.workflows["u3_quiz_generation"].call_count, 1)

    def test_soft_cap_emits_warning(self) -> None:
        meter = UsageMeter()
        meter.set_budget_caps("tenant-1", soft_limit_usd=0.05, hard_limit_usd=0.10)

        decision = meter.record_llm_call(
            tenant_id="tenant-1",
            workflow_id="u2_module_summary",
            input_tokens=5,
            output_tokens=5,
            estimated_cost_usd=0.05,
        )

        self.assertIsNotNone(decision.warning)

    def test_hard_cap_blocks_new_calls(self) -> None:
        meter = UsageMeter()
        meter.set_budget_caps("tenant-1", soft_limit_usd=0.05, hard_limit_usd=0.06)

        meter.record_llm_call(
            tenant_id="tenant-1",
            workflow_id="u2_module_summary",
            input_tokens=10,
            output_tokens=10,
            estimated_cost_usd=0.05,
        )

        with self.assertRaises(HardBudgetCapExceeded):
            meter.record_llm_call(
                tenant_id="tenant-1",
                workflow_id="u2_module_summary",
                input_tokens=1,
                output_tokens=1,
                estimated_cost_usd=0.02,
            )


if __name__ == "__main__":
    unittest.main()
