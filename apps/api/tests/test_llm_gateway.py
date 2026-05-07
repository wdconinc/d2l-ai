from __future__ import annotations

import pytest

from app.audit.log import AuditLogWriter
from app.llm.gateway import LLMGateway, ProviderRouter, RoutingRule
from app.llm.providers import (
    AzureOpenAIAdapter,
    BedrockAnthropicAdapter,
    ProviderResponse,
    VLLMAdapter,
)
from app.llm.scrub import PIIScrubber
from app.llm.types import LLMRequest, TokenUsage


class SpyProvider:
    provider_name = "spy"

    def __init__(self) -> None:
        self.last_prompt: str | None = None
        self.last_model: str | None = None
        self.last_correlation_id: str | None = None

    def generate(self, *, model: str, prompt: str, correlation_id: str) -> ProviderResponse:
        self.last_prompt = prompt
        self.last_model = model
        self.last_correlation_id = correlation_id
        usage = TokenUsage(prompt_tokens=3, completion_tokens=2, total_tokens=5)
        return ProviderResponse(text=f"generated:{prompt}", usage=usage)


def test_gateway_routes_by_tenant_and_model() -> None:
    provider = SpyProvider()
    router = ProviderRouter(
        rules=[
            RoutingRule(
                tenant_id="tenant-a",
                model="summary",
                provider_key="spy",
                provider_model="model-x",
            )
        ]
    )
    gateway = LLMGateway(
        providers={"spy": provider},
        router=router,
        scrubber=PIIScrubber(),
        audit_log=AuditLogWriter(),
    )

    response = gateway.generate(
        LLMRequest(
            tenant_id="tenant-a",
            model="summary",
            prompt="hello world",
            correlation_id="corr-1",
        )
    )

    assert provider.last_model == "model-x"
    assert response.metadata.model == "model-x"
    assert response.metadata.provider == "spy"


def test_gateway_scrubs_pii_before_provider_call() -> None:
    provider = SpyProvider()
    router = ProviderRouter(
        rules=[
            RoutingRule(
                tenant_id="tenant-a",
                model="summary",
                provider_key="spy",
                provider_model="model-x",
            )
        ]
    )
    gateway = LLMGateway(
        providers={"spy": provider},
        router=router,
        scrubber=PIIScrubber(),
        audit_log=AuditLogWriter(),
    )

    gateway.generate(
        LLMRequest(
            tenant_id="tenant-a",
            model="summary",
            prompt="Student email jane.doe@example.ca and id 12345678",
            correlation_id="corr-2",
        )
    )

    assert provider.last_prompt is not None
    assert "jane.doe@example.ca" not in provider.last_prompt
    assert "12345678" not in provider.last_prompt
    assert "[REDACTED_EMAIL]" in provider.last_prompt
    assert "[REDACTED_ID]" in provider.last_prompt


def test_gateway_does_not_scrub_unlabeled_long_numbers() -> None:
    provider = SpyProvider()
    router = ProviderRouter(
        rules=[
            RoutingRule(
                tenant_id="tenant-a",
                model="summary",
                provider_key="spy",
                provider_model="model-x",
            )
        ]
    )
    gateway = LLMGateway(
        providers={"spy": provider},
        router=router,
        scrubber=PIIScrubber(),
        audit_log=AuditLogWriter(),
    )

    gateway.generate(
        LLMRequest(
            tenant_id="tenant-a",
            model="summary",
            prompt="Reference number 20250507 should remain.",
            correlation_id="corr-2b",
        )
    )

    assert provider.last_prompt is not None
    assert "20250507" in provider.last_prompt


def test_gateway_writes_audit_log_with_required_fields() -> None:
    provider = SpyProvider()
    audit_log = AuditLogWriter()
    router = ProviderRouter(
        rules=[
            RoutingRule(
                tenant_id="tenant-b",
                model="rewrite",
                provider_key="spy",
                provider_model="model-y",
            )
        ]
    )
    gateway = LLMGateway(
        providers={"spy": provider},
        router=router,
        scrubber=PIIScrubber(),
        audit_log=audit_log,
    )

    response = gateway.generate(
        LLMRequest(
            tenant_id="tenant-b",
            model="rewrite",
            prompt="draft this content",
            correlation_id="corr-3",
        )
    )

    assert len(audit_log.entries) == 1
    entry = audit_log.entries[0]
    assert entry.model == "model-y"
    assert entry.prompt_hash == response.metadata.prompt_hash
    assert entry.response_hash == response.metadata.response_hash
    assert entry.total_tokens == 5
    assert entry.correlation_id == "corr-3"


def test_azure_adapter_rejects_non_canadian_endpoint() -> None:
    with pytest.raises(ValueError):
        AzureOpenAIAdapter(endpoint="https://eastus.api.cognitive.microsoft.com")


def test_bedrock_adapter_rejects_non_canadian_region() -> None:
    with pytest.raises(ValueError):
        BedrockAnthropicAdapter(region="us-east-1")


def test_vllm_adapter_generates_response() -> None:
    adapter = VLLMAdapter()
    response = adapter.generate(model="llama-3.1-70b", prompt="hi", correlation_id="corr-9")
    assert "[vllm:llama-3.1-70b]" in response.text


def test_vllm_adapter_rejects_non_canadian_remote_endpoint() -> None:
    with pytest.raises(ValueError):
        VLLMAdapter(endpoint="https://api.example.com")


def test_vllm_adapter_rejects_insecure_remote_endpoint() -> None:
    with pytest.raises(ValueError):
        VLLMAdapter(endpoint="http://vllm.canada.example.ca")
