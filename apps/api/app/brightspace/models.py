from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PagingInfo(BaseModel):
    has_more_items: bool = Field(default=False, alias="HasMoreItems")
    bookmark: str | None = Field(default=None, alias="Bookmark")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list, alias="Objects")
    paging_info: PagingInfo | None = Field(default=None, alias="PagingInfo")


class ContentModule(BaseModel):
    module_id: int = Field(alias="ModuleId")
    title: str = Field(alias="Title")


class ContentTopic(BaseModel):
    topic_id: int = Field(alias="TopicId")
    title: str = Field(alias="Title")
    url: str | None = Field(default=None, alias="Url")


class Quiz(BaseModel):
    quiz_id: int = Field(alias="QuizId")
    name: str = Field(alias="Name")


class QuestionLibraryQuestion(BaseModel):
    question_id: int = Field(alias="QuestionId")
    title: str = Field(alias="Title")
    question_type: str = Field(alias="QuestionType")


class Rubric(BaseModel):
    rubric_id: int = Field(alias="RubricId")
    name: str = Field(alias="Name")


class CreatedArtifact(BaseModel):
    id: int = Field(alias="Id")
    generated_at: datetime | None = Field(default=None, alias="GeneratedAt")
