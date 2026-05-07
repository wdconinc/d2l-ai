from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import sleep as default_sleep
from typing import Any, TypeVar

import httpx
from pydantic import TypeAdapter

from app.brightspace.models import (
    ContentModule,
    ContentTopic,
    CreatedArtifact,
    PagingInfo,
    QuestionLibraryQuestion,
    Quiz,
    Rubric,
)

T = TypeVar("T")


@dataclass(frozen=True)
class BrightspaceApiConfig:
    base_url: str
    le_version: str = "1.75"
    timeout_seconds: float = 20.0
    max_retries: int = 3
    backoff_seconds: float = 0.25


class BrightspaceApiClient:
    def __init__(
        self,
        config: BrightspaceApiConfig,
        *,
        http_client: httpx.Client | None = None,
        sleep: Callable[[float], None] = default_sleep,
    ) -> None:
        self.config = config
        self._sleep = sleep
        self._http_client = http_client or httpx.Client(timeout=config.timeout_seconds)

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.config.base_url}/d2l/api{path}"

        for attempt in range(self.config.max_retries + 1):
            response = self._http_client.request(method, url, **kwargs)
            if response.status_code not in {429, 503}:
                response.raise_for_status()
                return response

            if attempt >= self.config.max_retries:
                response.raise_for_status()

            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait_time = float(retry_after)
            else:
                wait_time = self.config.backoff_seconds * (2**attempt)
            self._sleep(wait_time)

        raise RuntimeError("request retry loop exited unexpectedly")

    def _get_paginated(self, path: str, model_type: type[T]) -> list[T]:
        results: list[T] = []
        bookmark: str | None = None
        item_adapter = TypeAdapter(model_type)
        paging_info_adapter: TypeAdapter[PagingInfo | None] = TypeAdapter(PagingInfo | None)

        while True:
            params = {"bookmark": bookmark} if bookmark else None
            response = self._request("GET", path, params=params)
            payload = response.json()
            for item in payload.get("Objects", []):
                results.append(item_adapter.validate_python(item))
            paging_info = paging_info_adapter.validate_python(payload.get("PagingInfo"))

            if not paging_info or not paging_info.has_more_items:
                return results
            bookmark = paging_info.bookmark


class ContentClient(BrightspaceApiClient):
    def list_modules(self, org_unit_id: int) -> list[ContentModule]:
        path = f"/le/{self.config.le_version}/{org_unit_id}/content/modules/"
        return self._get_paginated(path, ContentModule)

    def list_topics(self, org_unit_id: int, module_id: int) -> list[ContentTopic]:
        path = f"/le/{self.config.le_version}/{org_unit_id}/content/modules/{module_id}/structure/"
        return self._get_paginated(path, ContentTopic)

    def get_topic(self, org_unit_id: int, topic_id: int) -> ContentTopic:
        path = f"/le/{self.config.le_version}/{org_unit_id}/content/topics/{topic_id}"
        response = self._request("GET", path)
        return TypeAdapter(ContentTopic).validate_python(response.json())


class QuizzesClient(BrightspaceApiClient):
    def list_quizzes(self, org_unit_id: int) -> list[Quiz]:
        path = f"/le/{self.config.le_version}/{org_unit_id}/quizzes/"
        return self._get_paginated(path, Quiz)


class QuestionLibraryClient(BrightspaceApiClient):
    def list_questions(self, org_unit_id: int, section_id: int) -> list[QuestionLibraryQuestion]:
        path = (
            f"/le/{self.config.le_version}/{org_unit_id}/questionLibrary/sections/"
            f"{section_id}/questions/"
        )
        return self._get_paginated(path, QuestionLibraryQuestion)

    def create_question(
        self,
        org_unit_id: int,
        *,
        payload: dict[str, Any],
        confirm_write: bool = False,
    ) -> CreatedArtifact:
        if not confirm_write:
            raise PermissionError("confirm_write=True is required for write operations")

        path = f"/le/{self.config.le_version}/{org_unit_id}/questionLibrary/questions/"
        response = self._request("POST", path, json=payload)
        return TypeAdapter(CreatedArtifact).validate_python(response.json())


class RubricsClient(BrightspaceApiClient):
    def list_rubrics(self, org_unit_id: int) -> list[Rubric]:
        path = f"/le/{self.config.le_version}/{org_unit_id}/rubrics/"
        return self._get_paginated(path, Rubric)

    def create_rubric(
        self,
        org_unit_id: int,
        *,
        payload: dict[str, Any],
        confirm_write: bool = False,
    ) -> CreatedArtifact:
        if not confirm_write:
            raise PermissionError("confirm_write=True is required for write operations")

        path = f"/le/{self.config.le_version}/{org_unit_id}/rubrics/"
        response = self._request("POST", path, json=payload)
        return TypeAdapter(CreatedArtifact).validate_python(response.json())
