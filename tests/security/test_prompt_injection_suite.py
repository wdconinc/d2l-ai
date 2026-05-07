from __future__ import annotations

import json
import unittest
from pathlib import Path

from docs.prompts.security.harness import (
    ProviderMock,
    REFUSAL_MESSAGE,
    run_with_provider,
    sanitize_html_topic,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "prompts"
    / "security"
    / "fixtures"
    / "prompt_injection_cases.json"
)


class PromptInjectionSecurityTests(unittest.TestCase):
    def test_refuses_secret_system_prompt_and_roster_requests(self) -> None:
        fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

        for case in fixtures:
            with self.subTest(case_id=case["id"]):
                provider = ProviderMock()
                response = run_with_provider(
                    provider=provider,
                    user_request=case["user_request"],
                    rag_context=case.get("rag_context", ""),
                    html_content=case.get("html_content", ""),
                )

                if case["kind"] in {
                    "system_prompt_leakage",
                    "token_exfiltration",
                    "rag_roster_exfiltration",
                }:
                    self.assertEqual(response, REFUSAL_MESSAGE)
                    self.assertIsNone(provider.last_prompt)

    def test_malicious_html_fixture_is_neutralized(self) -> None:
        fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        html_case = next(case for case in fixtures if case["kind"] == "html_rewrite_injection")

        sanitized = sanitize_html_topic(html_case["html_content"])
        self.assertNotIn("<script", sanitized.lower())
        self.assertNotIn("onclick=", sanitized.lower())
        self.assertNotIn("reveal system prompt", sanitized.lower())

    def test_provider_mock_receives_scrubbed_prompt(self) -> None:
        provider = ProviderMock()
        response = run_with_provider(
            provider=provider,
            user_request="Create an instructor-facing module overview draft.",
            rag_context=(
                "Roster:\nAlice Wong, Student ID 7900123\n"
                "oauth refresh_token=abc123SECRET987654321"
            ),
        )

        self.assertEqual(response, "Safe draft output.")
        self.assertIsNotNone(provider.last_prompt)
        prompt = provider.last_prompt or ""
        self.assertNotIn("7900123", prompt)
        self.assertNotIn("Alice Wong", prompt)
        self.assertNotIn("abc123SECRET987654321", prompt)
        self.assertNotIn("refresh_token", prompt.lower())


if __name__ == "__main__":
    unittest.main()
