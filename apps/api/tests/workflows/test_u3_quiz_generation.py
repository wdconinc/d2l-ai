from __future__ import annotations

import pytest

from app.brightspace.question_library_client import QuestionLibraryWriteRequest
from app.workflows.u3_quiz_generation import (
    QuizGenerationRequest,
    QuizSchemaError,
    QuestionItem,
    U3QuizGenerationWorkflow,
)


class FakeQuestionLibraryClient:
    def __init__(self) -> None:
        self.requests: list[QuestionLibraryWriteRequest] = []

    def create_question(self, request: QuestionLibraryWriteRequest) -> str:
        self.requests.append(request)
        return f"written-{len(self.requests)}"


class FailingQuestionLibraryClient(FakeQuestionLibraryClient):
    def create_question(self, request: QuestionLibraryWriteRequest) -> str:
        raise RuntimeError("write failed")


def _build_workflow(llm_payload: str, client: FakeQuestionLibraryClient | None = None) -> U3QuizGenerationWorkflow:
    fake_client = client or FakeQuestionLibraryClient()
    return U3QuizGenerationWorkflow(
        llm_generate=lambda _: llm_payload,
        scrub_payload=lambda payload: payload,
        question_library_client=fake_client,
        model="test-model",
    )


def test_generate_preview_validates_questions_and_provenance() -> None:
    workflow = _build_workflow(
        """
        {"questions":[
          {"item_id":"q1","question_type":"mcq","question_text":"2+2?","options":[{"text":"3","is_correct":false},{"text":"4","is_correct":true}]},
          {"item_id":"q2","question_type":"short_answer","question_text":"Explain gravity.","answer_text":"It is attraction between masses."}
        ]}
        """
    )

    preview = workflow.generate_preview(
        QuizGenerationRequest(
            org_unit_id=10,
            module_id=2,
            topic_ids=[1, 2],
            readings=["Topic 1", "Topic 2"],
        )
    )

    assert len(preview.questions) == 2
    assert preview.questions[0].question_type == "mcq"
    assert preview.questions[1].question_type == "short_answer"
    assert preview.model == "test-model"
    assert preview.version == "u3.v1"
    assert preview.prompt_hash
    assert preview.generated_at


def test_generate_preview_repairs_fenced_json_and_alias_type() -> None:
    workflow = _build_workflow(
        """```json
        {"questions":[{"question_type":"multiple_choice","question_text":"Pick one","options":[{"text":"A","is_correct":true},{"text":"B","is_correct":false}]}]}
        ```"""
    )

    preview = workflow.generate_preview(
        QuizGenerationRequest(org_unit_id=10, module_id=2, topic_ids=[1], readings=["Topic"])
    )

    assert preview.questions[0].question_type == "mcq"
    assert preview.questions[0].item_id == "q1"


def test_generate_preview_rejects_malformed_json() -> None:
    workflow = _build_workflow('{"questions":[{"question_type":"mcq",}')

    with pytest.raises(QuizSchemaError):
        workflow.generate_preview(
            QuizGenerationRequest(org_unit_id=10, module_id=2, topic_ids=[1], readings=["Topic"])
        )


def test_generate_preview_rejects_unexpected_fields() -> None:
    workflow = _build_workflow(
        """
        {"questions":[
          {"question_type":"short_answer","question_text":"Q","answer_text":"A","difficulty":"hard"}
        ]}
        """
    )

    with pytest.raises(QuizSchemaError):
        workflow.generate_preview(
            QuizGenerationRequest(org_unit_id=10, module_id=2, topic_ids=[1], readings=["Topic"])
        )


def test_write_to_question_library_requires_confirmation() -> None:
    client = FakeQuestionLibraryClient()
    workflow = _build_workflow(
        '{"questions":[{"question_type":"short_answer","question_text":"Q","answer_text":"A"}]}', client
    )
    preview = workflow.generate_preview(
        QuizGenerationRequest(org_unit_id=10, module_id=2, topic_ids=[1], readings=["Topic"])
    )

    with pytest.raises(PermissionError):
        workflow.write_to_question_library(org_unit_id=10, questions=preview.questions, confirmed=False)
    assert client.requests == []


def test_write_to_question_library_uses_typed_client_after_confirmation() -> None:
    client = FakeQuestionLibraryClient()
    workflow = _build_workflow(
        '{"questions":[{"question_type":"short_answer","question_text":"Original","answer_text":"A"}]}',
        client,
    )
    preview = workflow.generate_preview(
        QuizGenerationRequest(org_unit_id=10, module_id=2, topic_ids=[1], readings=["Topic"])
    )
    edited = [
        QuestionItem(
            item_id=preview.questions[0].item_id,
            question_type=preview.questions[0].question_type,
            question_text="Edited text",
            answer_text=preview.questions[0].answer_text,
        )
    ]

    write_ids = workflow.write_to_question_library(org_unit_id=10, questions=edited, confirmed=True)

    assert write_ids == ["written-1"]
    assert client.requests[0].question_text == "Edited text"


def test_write_to_question_library_surfaces_client_failures() -> None:
    workflow = _build_workflow(
        '{"questions":[{"question_type":"short_answer","question_text":"Q","answer_text":"A"}]}',
        FailingQuestionLibraryClient(),
    )
    preview = workflow.generate_preview(
        QuizGenerationRequest(org_unit_id=10, module_id=2, topic_ids=[1], readings=["Topic"])
    )

    with pytest.raises(RuntimeError, match="write failed"):
        workflow.write_to_question_library(org_unit_id=10, questions=preview.questions, confirmed=True)
