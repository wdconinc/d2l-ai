from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable

from app.brightspace.question_library_client import (
    QuestionLibraryClient,
    QuestionLibraryWriteRequest,
)


class QuizSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class QuizGenerationRequest:
    org_unit_id: int
    module_id: int
    topic_ids: list[int]
    readings: list[str]
    max_questions: int = 5


@dataclass(frozen=True)
class QuestionItem:
    item_id: str
    question_type: str
    question_text: str
    options: list[dict[str, object]] | None = None
    answer_text: str | None = None
    feedback: str | None = None


@dataclass(frozen=True)
class QuizPreview:
    questions: list[QuestionItem]
    model: str
    prompt_hash: str
    version: str
    generated_at: str


class U3QuizGenerationWorkflow:
    def __init__(
        self,
        *,
        llm_generate: Callable[[dict[str, Any]], str],
        scrub_payload: Callable[[dict[str, Any]], dict[str, Any]],
        question_library_client: QuestionLibraryClient,
        model: str,
        prompt_version: str = "u3.v1",
    ) -> None:
        self._llm_generate = llm_generate
        self._scrub_payload = scrub_payload
        self._question_library_client = question_library_client
        self._model = model
        self._prompt_version = prompt_version

    def generate_preview(self, request: QuizGenerationRequest) -> QuizPreview:
        payload = {
            "module_id": request.module_id,
            "topic_ids": request.topic_ids,
            "readings": request.readings,
            "max_questions": request.max_questions,
        }
        scrubbed_payload = self._scrub_payload(payload)
        generated_at = datetime.now(UTC).isoformat()
        raw_response = self._llm_generate(scrubbed_payload)
        questions = self._parse_questions(raw_response)
        prompt_hash = hashlib.sha256(
            json.dumps(scrubbed_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return QuizPreview(
            questions=questions,
            model=self._model,
            prompt_hash=prompt_hash,
            version=self._prompt_version,
            generated_at=generated_at,
        )

    def write_to_question_library(
        self, *, org_unit_id: int, questions: list[QuestionItem], confirmed: bool
    ) -> list[str]:
        if not confirmed:
            raise PermissionError("Explicit instructor confirmation is required before write-back.")
        write_ids: list[str] = []
        for question in questions:
            write_ids.append(
                self._question_library_client.create_question(
                    QuestionLibraryWriteRequest(
                        org_unit_id=org_unit_id,
                        question_text=question.question_text,
                        question_type=question.question_type,
                        options=question.options,
                        answer_text=question.answer_text,
                        feedback=question.feedback,
                    )
                )
            )
        return write_ids

    def _parse_questions(self, raw_response: str) -> list[QuestionItem]:
        parsed_response = self._parse_json_with_repairs(raw_response)
        questions_raw = self._extract_questions(parsed_response)
        if not questions_raw:
            raise QuizSchemaError("No questions were generated.")
        validated_questions = [
            self._validate_question(question, idx + 1) for idx, question in enumerate(questions_raw)
        ]
        return validated_questions

    def _parse_json_with_repairs(self, raw_response: str) -> Any:
        raw_response = raw_response.strip()
        candidates = [raw_response]
        if "```json" in raw_response:
            start = raw_response.find("```json") + len("```json")
            end = raw_response.find("```", start)
            if end > start:
                candidates.append(raw_response[start:end].strip())
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise QuizSchemaError("LLM output is not valid JSON.")

    def _extract_questions(self, parsed_response: Any) -> list[dict[str, Any]]:
        if isinstance(parsed_response, list):
            return parsed_response
        if isinstance(parsed_response, dict):
            questions = parsed_response.get("questions")
            if isinstance(questions, list):
                return questions
        raise QuizSchemaError("LLM output must be an array or an object with a 'questions' array.")

    def _validate_question(self, question: Any, default_index: int) -> QuestionItem:
        if not isinstance(question, dict):
            raise QuizSchemaError("Each generated question must be a JSON object.")

        question_type_aliases = {
            "multiple_choice": "mcq",
            "multiple-choice": "mcq",
            "short-answer": "short_answer",
        }
        question_type_raw = question.get("question_type")
        question_type = question_type_aliases.get(question_type_raw, question_type_raw)
        if question_type not in {"mcq", "short_answer"}:
            raise QuizSchemaError("question_type must be either 'mcq' or 'short_answer'.")

        item_id = str(question.get("item_id", f"q{default_index}"))
        question_text = question.get("question_text")
        feedback = question.get("feedback")
        if not isinstance(question_text, str) or not question_text.strip():
            raise QuizSchemaError("question_text must be a non-empty string.")
        if feedback is not None and not isinstance(feedback, str):
            raise QuizSchemaError("feedback must be a string when provided.")

        allowed_fields = {"item_id", "question_type", "question_text", "feedback"}
        options: list[dict[str, object]] | None = None
        answer_text: str | None = None

        if question_type == "mcq":
            allowed_fields.add("options")
            options = question.get("options")
            if not isinstance(options, list) or len(options) < 2:
                raise QuizSchemaError("MCQ items require at least 2 options.")
            cleaned_options: list[dict[str, object]] = []
            correct_answers = 0
            for option in options:
                if not isinstance(option, dict):
                    raise QuizSchemaError("Each option must be an object.")
                if set(option.keys()) != {"text", "is_correct"}:
                    raise QuizSchemaError(
                        f"Each option must contain only 'text' and 'is_correct'; got {sorted(option.keys())}."
                    )
                if not isinstance(option["text"], str) or not option["text"].strip():
                    raise QuizSchemaError("Option text must be a non-empty string.")
                if not isinstance(option["is_correct"], bool):
                    raise QuizSchemaError("Option is_correct must be a boolean.")
                if option["is_correct"]:
                    correct_answers += 1
                cleaned_options.append({"text": option["text"], "is_correct": option["is_correct"]})
            if correct_answers != 1:
                raise QuizSchemaError("MCQ items must have exactly one correct answer.")
            options = cleaned_options
        else:
            allowed_fields.add("answer_text")
            answer_text_raw = question.get("answer_text")
            if not isinstance(answer_text_raw, str) or not answer_text_raw.strip():
                raise QuizSchemaError("short_answer items require non-empty answer_text.")
            answer_text = answer_text_raw

        extra_fields = set(question.keys()) - allowed_fields
        if extra_fields:
            raise QuizSchemaError(f"Unexpected fields in question payload: {sorted(extra_fields)}")

        return QuestionItem(
            item_id=item_id,
            question_type=question_type,
            question_text=question_text,
            options=options,
            answer_text=answer_text,
            feedback=feedback,
        )
