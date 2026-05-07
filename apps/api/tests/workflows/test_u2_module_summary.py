from __future__ import annotations

import asyncio

from app.brightspace.content_client import ModuleTopic
from app.workflows.u2_module_summary import (
    ModuleSummaryDraft,
    generate_u2_module_summary,
)


class StubContentClient:
    def __init__(self, topics: list[ModuleTopic]) -> None:
        self._topics = topics

    async def list_module_topics(self, org_unit_id: int, module_id: int) -> list[ModuleTopic]:
        assert org_unit_id > 0
        assert module_id > 0
        return self._topics


class CapturingLLMGateway:
    def __init__(self) -> None:
        self.last_prompt = ""

    async def summarize_module(self, prompt: str) -> ModuleSummaryDraft:
        self.last_prompt = prompt
        return ModuleSummaryDraft(
            summary="This module introduces key concepts.",
            suggested_outcomes=["Explain concept A", "Apply concept B"],
            time_on_task_minutes=45,
            model="test-model",
        )


def test_generate_u2_module_summary_empty_module() -> None:
    content_client = StubContentClient(topics=[])
    llm_gateway = CapturingLLMGateway()

    result = asyncio.run(
        generate_u2_module_summary(
            org_unit_id=1,
            module_id=2,
            content_client=content_client,
            llm_gateway=llm_gateway,
        )
    )

    assert "No supported topic content was found." in llm_gateway.last_prompt
    assert result.summary == "This module introduces key concepts."
    assert result.suggested_outcomes == ["Explain concept A", "Apply concept B"]
    assert result.time_on_task_minutes == 45
    assert result.deep_linking_payload is None


def test_generate_u2_module_summary_long_module_limits_prompt() -> None:
    long_text = "A" * 20_000
    topics = [ModuleTopic(id=1, title="Huge topic", topic_type="text", content=long_text)]
    content_client = StubContentClient(topics=topics)
    llm_gateway = CapturingLLMGateway()

    asyncio.run(
        generate_u2_module_summary(
            org_unit_id=1,
            module_id=2,
            content_client=content_client,
            llm_gateway=llm_gateway,
            deep_link_title="Module 1 Overview",
        )
    )

    assert len(llm_gateway.last_prompt) <= 12_000
    assert "Huge topic" in llm_gateway.last_prompt


def test_generate_u2_module_summary_ignores_unsupported_topic_types() -> None:
    topics = [
        ModuleTopic(id=1, title="Video", topic_type="video", content="ignored"),
        ModuleTopic(id=2, title="HTML", topic_type="html", content="<p>Use this text.</p>"),
    ]
    content_client = StubContentClient(topics=topics)
    llm_gateway = CapturingLLMGateway()

    result = asyncio.run(
        generate_u2_module_summary(
            org_unit_id=1,
            module_id=2,
            content_client=content_client,
            llm_gateway=llm_gateway,
            deep_link_title="Module 1 Overview",
        )
    )

    assert "Video: ignored" not in llm_gateway.last_prompt
    assert "HTML: Use this text." in llm_gateway.last_prompt
    assert result.deep_linking_payload is not None
    assert "<!-- generated-by: UM-AI-Tool" in result.deep_linking_payload.html


def test_generate_u2_module_summary_scrubs_student_identifiers() -> None:
    topics = [
        ModuleTopic(
            id=1,
            title="Roster Notes",
            topic_type="text",
            content="Student Name: Alex Learner, Email: alex@example.com, ID: 1234567",
        ),
    ]
    content_client = StubContentClient(topics=topics)
    llm_gateway = CapturingLLMGateway()

    asyncio.run(
        generate_u2_module_summary(
            org_unit_id=1,
            module_id=2,
            content_client=content_client,
            llm_gateway=llm_gateway,
        )
    )

    assert "Alex Learner" not in llm_gateway.last_prompt
    assert "alex@example.com" not in llm_gateway.last_prompt
    assert "1234567" not in llm_gateway.last_prompt
