from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from app.brightspace.clients import (
    BrightspaceApiConfig,
    ContentClient,
    QuestionLibraryClient,
    RubricsClient,
)


def _build_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_list_modules_handles_pagination() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            assert request.url.params.get("bookmark") is None
            return httpx.Response(
                200,
                json={
                    "Objects": [{"ModuleId": 1, "Title": "Week 1"}],
                    "PagingInfo": {"HasMoreItems": True, "Bookmark": "next-page"},
                },
            )

        assert request.url.params.get("bookmark") == "next-page"
        return httpx.Response(
            200,
            json={
                "Objects": [{"ModuleId": 2, "Title": "Week 2"}],
                "PagingInfo": {"HasMoreItems": False, "Bookmark": None},
            },
        )

    client = ContentClient(
        BrightspaceApiConfig(base_url="https://tenant.brightspace.com"),
        http_client=_build_client(handler),
    )

    modules = client.list_modules(org_unit_id=999)

    assert [module.module_id for module in modules] == [1, 2]
    assert call_count == 2


def test_rate_limit_retries_429_and_503_then_succeeds() -> None:
    statuses = [429, 503, 200]
    sleep_calls: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        status = statuses.pop(0)
        headers = {"Retry-After": "1"} if status == 429 else {}
        body = {
            "Objects": [{"RubricId": 7, "Name": "Essay"}],
            "PagingInfo": {"HasMoreItems": False},
        }
        return httpx.Response(status, headers=headers, json=body)

    client = RubricsClient(
        BrightspaceApiConfig(
            base_url="https://tenant.brightspace.com",
            max_retries=3,
            backoff_seconds=0.1,
        ),
        http_client=_build_client(handler),
        sleep=sleep_calls.append,
    )

    rubrics = client.list_rubrics(org_unit_id=11)

    assert [rubric.rubric_id for rubric in rubrics] == [7]
    assert sleep_calls == [1.0, 0.2]


def test_create_question_requires_explicit_confirmation() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        pytest.fail("HTTP request should not execute without confirm_write=True")

    client = QuestionLibraryClient(
        BrightspaceApiConfig(base_url="https://tenant.brightspace.com"),
        http_client=_build_client(handler),
    )

    with pytest.raises(PermissionError, match="confirm_write"):
        client.create_question(org_unit_id=1, payload={"Title": "Q1"})


def test_configurable_api_version_is_used_in_paths() -> None:
    captured_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_paths.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "Objects": [{"TopicId": 42, "Title": "Intro", "Url": "https://example.test/topic"}],
                "PagingInfo": {"HasMoreItems": False},
            },
        )

    client = ContentClient(
        BrightspaceApiConfig(base_url="https://tenant.brightspace.com", le_version="1.82"),
        http_client=_build_client(handler),
    )

    client.list_topics(org_unit_id=222, module_id=5)

    assert captured_paths == ["/d2l/api/le/1.82/222/content/modules/5/structure/"]
