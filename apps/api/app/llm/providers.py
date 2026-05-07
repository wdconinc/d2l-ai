from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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
        usage = TokenUsage(prompt_tokens=max(len(prompt.split()), 1), completion_tokens=6, total_tokens=0)
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        return ProviderResponse(text=f"[bedrock:{model}] {prompt}", usage=usage)


class VLLMAdapter:
    provider_name = "vllm"

    def __init__(self, endpoint: str = "http://localhost:8000") -> None:
        self.endpoint = endpoint

    def generate(self, *, model: str, prompt: str, correlation_id: str) -> ProviderResponse:
        _ = correlation_id
        usage = TokenUsage(prompt_tokens=max(len(prompt.split()), 1), completion_tokens=4, total_tokens=0)
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        return ProviderResponse(text=f"[vllm:{model}] {prompt}", usage=usage)
