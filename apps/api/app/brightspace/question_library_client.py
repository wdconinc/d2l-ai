from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class QuestionLibraryWriteRequest:
    org_unit_id: int
    question_text: str
    question_type: str
    options: list[dict[str, str | bool]] | None = None
    answer_text: str | None = None
    feedback: str | None = None


class QuestionLibraryClient(Protocol):
    """Typed boundary for Question Library write operations."""

    def create_question(self, request: QuestionLibraryWriteRequest) -> str:
        ...
