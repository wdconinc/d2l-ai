from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(slots=True)
class LLMRequest:
    tenant_id: str
    model: str
    prompt: str
    correlation_id: str


@dataclass(slots=True)
class LLMMetadata:
    provider: str
    model: str
    prompt_hash: str
    response_hash: str
    version: str
    generated_at: datetime
    token_usage: TokenUsage
    correlation_id: str


@dataclass(slots=True)
class LLMResponse:
    text: str
    metadata: LLMMetadata
