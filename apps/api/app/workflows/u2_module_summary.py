from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from html import escape
from html import unescape
import json
import re
from typing import Protocol, Sequence

from app.brightspace.content_client import BrightspaceContentClient, ModuleTopic
from app.llm.scrub import scrub_prompt_text

_SUPPORTED_TOPIC_TYPES = {"html", "text", "markdown"}
# Keep per-topic excerpts small to avoid sending unnecessary content to the LLM.
_MAX_TOPIC_CHARS = 2_500
# Keep entire prompt bounded for predictable latency/cost and model context usage.
_MAX_PROMPT_CHARS = 12_000
_WORKFLOW_VERSION = "u2.v1"
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(slots=True, frozen=True)
class ModuleSummaryDraft:
    summary: str
    suggested_outcomes: list[str]
    time_on_task_minutes: int
    model: str


class ModuleSummaryLLMGateway(Protocol):
    async def summarize_module(self, prompt: str) -> ModuleSummaryDraft:
        """Summarize a module from prepared prompt text."""


@dataclass(slots=True, frozen=True)
class WorkflowProvenance:
    model: str
    prompt_hash: str
    version: str
    generated_at: str


@dataclass(slots=True, frozen=True)
class DeepLinkingPayload:
    title: str
    html: str
    metadata: dict[str, str]


@dataclass(slots=True, frozen=True)
class U2ModuleSummaryResult:
    summary: str
    suggested_outcomes: list[str]
    time_on_task_minutes: int
    preview_markdown: str
    provenance: WorkflowProvenance
    deep_linking_payload: DeepLinkingPayload | None


async def generate_u2_module_summary(
    *,
    org_unit_id: int,
    module_id: int,
    content_client: BrightspaceContentClient,
    llm_gateway: ModuleSummaryLLMGateway,
    deep_link_title: str | None = None,
) -> U2ModuleSummaryResult:
    topics = await content_client.list_module_topics(org_unit_id=org_unit_id, module_id=module_id)
    content_sections = _extract_supported_topic_text(topics)
    prompt = _build_prompt(content_sections)
    scrubbed_prompt = scrub_prompt_text(prompt)
    draft = await llm_gateway.summarize_module(scrubbed_prompt)

    prompt_hash = sha256(scrubbed_prompt.encode("utf-8")).hexdigest()
    generated_at = datetime.now(UTC).isoformat()
    provenance = WorkflowProvenance(
        model=draft.model,
        prompt_hash=prompt_hash,
        version=_WORKFLOW_VERSION,
        generated_at=generated_at,
    )
    preview_markdown = _build_preview_markdown(draft)
    deep_linking_payload = None
    if deep_link_title:
        deep_linking_payload = _build_deep_linking_payload(
            title=deep_link_title,
            preview_markdown=preview_markdown,
            provenance=provenance,
        )

    return U2ModuleSummaryResult(
        summary=draft.summary,
        suggested_outcomes=draft.suggested_outcomes,
        time_on_task_minutes=draft.time_on_task_minutes,
        preview_markdown=preview_markdown,
        provenance=provenance,
        deep_linking_payload=deep_linking_payload,
    )


def _extract_supported_topic_text(topics: Sequence[ModuleTopic]) -> list[str]:
    extracted: list[str] = []
    for topic in topics:
        topic_type = topic.topic_type.lower()
        if topic_type not in _SUPPORTED_TOPIC_TYPES:
            continue

        text = topic.content
        if topic_type == "html":
            text = _html_to_text(text)

        cleaned = _normalize_text(text)
        if not cleaned:
            continue

        excerpt = _truncate_preserving_words(cleaned, _MAX_TOPIC_CHARS)
        extracted.append(f"{topic.title}: {excerpt}")
    return extracted


def _build_prompt(content_sections: Sequence[str]) -> str:
    if not content_sections:
        return (
            "Summarize this module for instructors.\n"
            "No supported topic content was found.\n"
            "Return concise summary, 2-4 suggested outcomes, and estimated time-on-task minutes."
        )

    parts = [
        "Summarize this Brightspace module for instructor preview.",
        "Return: summary, 2-4 suggested outcomes, and estimated time-on-task minutes.",
        "Use only the provided topic content.",
        "",
        "Module content:",
    ]
    current_size = sum(len(part) for part in parts)
    for section in content_sections:
        candidate = f"- {section}"
        if current_size + len(candidate) > _MAX_PROMPT_CHARS:
            break
        parts.append(candidate)
        current_size += len(candidate)
    return "\n".join(parts)


def _html_to_text(html: str) -> str:
    return unescape(_TAG_RE.sub(" ", html))


def _normalize_text(text: str) -> str:
    normalized_lines = [" ".join(line.split()) for line in text.splitlines()]
    kept_lines = [line for line in normalized_lines if line]
    return "\n".join(kept_lines).strip()


def _truncate_preserving_words(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    if " " not in truncated:
        return truncated
    return truncated.rsplit(" ", 1)[0]


def _build_preview_markdown(draft: ModuleSummaryDraft) -> str:
    cleaned_outcomes = [item.strip() for item in draft.suggested_outcomes if item.strip()]
    outcomes = "\n".join(f"- {item}" for item in cleaned_outcomes) or "- (none)"
    return (
        "## Module Summary\n"
        f"{draft.summary}\n\n"
        "## Suggested Learning Outcomes\n"
        f"{outcomes}\n\n"
        "## Estimated Time on Task\n"
        f"{draft.time_on_task_minutes} minutes"
    )


def _build_deep_linking_payload(
    *, title: str, preview_markdown: str, provenance: WorkflowProvenance
) -> DeepLinkingPayload:
    metadata = {
        "model": provenance.model,
        "prompt_hash": provenance.prompt_hash,
        "version": provenance.version,
        "generated_at": provenance.generated_at,
    }
    safe_version = _sanitize_for_html_comment(provenance.version)
    safe_model = _sanitize_for_html_comment(provenance.model)
    safe_prompt_hash = _sanitize_for_html_comment(provenance.prompt_hash)
    provenance_comment = (
        f"<!-- generated-by: UM-AI-Tool {safe_version}, model={safe_model}, "
        f"prompt-hash={safe_prompt_hash} -->"
    )
    # Prevent accidental script-tag termination if metadata ever contains '</script>'.
    metadata_json = json.dumps(metadata, ensure_ascii=True).replace("</", "<\\/")
    html = (
        f"{provenance_comment}\n"
        "<article>\n"
        f"<h1>{escape(title)}</h1>\n"
        f"<pre>{escape(preview_markdown)}</pre>\n"
        f"<script type=\"application/json\" id=\"um-ai-provenance\">{metadata_json}</script>\n"
        "</article>"
    )
    return DeepLinkingPayload(title=title, html=html, metadata=metadata)


def _sanitize_for_html_comment(value: str) -> str:
    return value.replace("--", "- -").replace(">", "&gt;")
