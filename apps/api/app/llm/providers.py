from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

from app.llm.types import TokenUsage


@dataclass(slots=True)
class ProviderResponse:
    text: str
    usage: TokenUsage


class LLMProvider(Protocol):
    provider_name: str

    def generate(self, *, model: str, prompt: str, correlation_id: str) -> ProviderResponse: ...


class AzureOpenAIAdapter:
    provider_name = "azure_openai"

    def __init__(self, endpoint: str = "https://canadacentral.api.cognitive.microsoft.com") -> None:
        if "canadacentral" not in endpoint.lower():
            msg = "Azure OpenAI endpoint must be in Canada Central."
            raise ValueError(msg)
        self.endpoint = endpoint

    def generate(self, *, model: str, prompt: str, correlation_id: str) -> ProviderResponse:
        _ = correlation_id
        # Placeholder usage estimate until SDK integration returns provider token usage.
        usage = TokenUsage(prompt_tokens=max(len(prompt.split()), 1), completion_tokens=5, total_tokens=0)
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        return ProviderResponse(text=f"[azure:{model}] {prompt}", usage=usage)


class BedrockAnthropicAdapter:
    provider_name = "anthropic_bedrock"

    def __init__(self, region: str = "ca-central-1") -> None:
        if region != "ca-central-1":
            msg = "Bedrock Anthropic region must be ca-central-1."
            raise ValueError(msg)
        self.region = region

    def generate(self, *, model: str, prompt: str, correlation_id: str) -> ProviderResponse:
        _ = correlation_id
        # Placeholder usage estimate until SDK integration returns provider token usage.
        usage = TokenUsage(prompt_tokens=max(len(prompt.split()), 1), completion_tokens=6, total_tokens=0)
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        return ProviderResponse(text=f"[bedrock:{model}] {prompt}", usage=usage)


class VLLMAdapter:
    provider_name = "vllm"

    def __init__(self, endpoint: str = "http://localhost:8000") -> None:
        parsed = urlparse(endpoint)
        hostname = (parsed.hostname or "").lower()
        is_local = hostname in {"localhost", "127.0.0.1"}
        if parsed.scheme not in {"http", "https"}:
            msg = "vLLM endpoint must use http or https."
            raise ValueError(msg)
        if parsed.scheme == "http" and not is_local:
            msg = "Remote vLLM endpoints must use https."
            raise ValueError(msg)
        if not is_local and "canada" not in endpoint.lower() and not hostname.endswith(".ca"):
            msg = "Remote vLLM endpoints must stay in Canadian infrastructure."
            raise ValueError(msg)
        self.endpoint = endpoint

    def generate(self, *, model: str, prompt: str, correlation_id: str) -> ProviderResponse:
        _ = correlation_id
        # Placeholder usage estimate until SDK integration returns provider token usage.
        usage = TokenUsage(prompt_tokens=max(len(prompt.split()), 1), completion_tokens=4, total_tokens=0)
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        return ProviderResponse(text=f"[vllm:{model}] {prompt}", usage=usage)
