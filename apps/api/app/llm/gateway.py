from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from app.audit.log import AuditLogEntry, AuditLogWriter
from app.llm.providers import LLMProvider
from app.llm.scrub import PIIScrubber
from app.llm.types import LLMMetadata, LLMRequest, LLMResponse


@dataclass(frozen=True, slots=True)
class RoutingRule:
    tenant_id: str
    model: str
    provider_key: str
    provider_model: str


class ProviderRouter:
    def __init__(self, rules: list[RoutingRule]) -> None:
        self._routes = {(rule.tenant_id, rule.model): rule for rule in rules}

    def route(self, *, tenant_id: str, model: str) -> RoutingRule:
        key = (tenant_id, model)
        if key not in self._routes:
            msg = f"No provider route configured for tenant={tenant_id}, model={model}"
            raise KeyError(msg)
        return self._routes[key]


class LLMGateway:
    VERSION = "v1"

    def __init__(
        self,
        *,
        providers: dict[str, LLMProvider],
        router: ProviderRouter,
        scrubber: PIIScrubber,
        audit_log: AuditLogWriter,
    ) -> None:
        self._providers = providers
        self._router = router
        self._scrubber = scrubber
        self._audit_log = audit_log

    def generate(self, request: LLMRequest) -> LLMResponse:
        rule = self._router.route(tenant_id=request.tenant_id, model=request.model)
        provider = self._providers[rule.provider_key]
        scrubbed_prompt = self._scrubber.scrub(request.prompt)
        provider_response = provider.generate(
            model=rule.provider_model,
            prompt=scrubbed_prompt,
            correlation_id=request.correlation_id,
        )

        prompt_hash = _hash_text(scrubbed_prompt)
        response_hash = _hash_text(provider_response.text)
        now = datetime.now(UTC)

        self._audit_log.write(
            AuditLogEntry(
                tenant_id=request.tenant_id,
                provider=provider.provider_name,
                model=rule.provider_model,
                prompt_hash=prompt_hash,
                response_hash=response_hash,
                prompt_tokens=provider_response.usage.prompt_tokens,
                completion_tokens=provider_response.usage.completion_tokens,
                total_tokens=provider_response.usage.total_tokens,
                correlation_id=request.correlation_id,
                created_at=now,
            )
        )

        metadata = LLMMetadata(
            provider=provider.provider_name,
            model=rule.provider_model,
            prompt_hash=prompt_hash,
            response_hash=response_hash,
            version=self.VERSION,
            generated_at=now,
            token_usage=provider_response.usage,
            correlation_id=request.correlation_id,
        )
        return LLMResponse(text=provider_response.text, metadata=metadata)


def _hash_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()
