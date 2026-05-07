from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class AuditLogEntry:
    tenant_id: str
    provider: str
    model: str
    prompt_hash: str
    response_hash: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    correlation_id: str
    created_at: datetime


class AuditLogWriter:
    """Simple in-memory audit writer for gateway events."""

    def __init__(self) -> None:
        self.entries: list[AuditLogEntry] = []

    def write(self, entry: AuditLogEntry) -> None:
        if entry.created_at.tzinfo is None:
            entry.created_at = entry.created_at.replace(tzinfo=timezone.utc)
        self.entries.append(entry)
