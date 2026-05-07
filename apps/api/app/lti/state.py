from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe


@dataclass
class StateNonceRecord:
    nonce: str
    expires_at: datetime


class LTIStateNonceStore:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._states: dict[str, StateNonceRecord] = {}
        self._used_nonces: set[str] = set()

    def issue(self) -> tuple[str, str]:
        self._cleanup_expired()
        state = token_urlsafe(32)
        nonce = token_urlsafe(32)
        self._states[state] = StateNonceRecord(
            nonce=nonce,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds),
        )
        return state, nonce

    def consume(self, state: str, nonce: str) -> bool:
        self._cleanup_expired()
        record = self._states.pop(state, None)
        if record is None:
            return False
        if record.nonce != nonce:
            return False
        if nonce in self._used_nonces:
            return False
        self._used_nonces.add(nonce)
        return True

    def has_state(self, state: str) -> bool:
        self._cleanup_expired()
        return state in self._states

    def _cleanup_expired(self) -> None:
        now = datetime.now(timezone.utc)
        expired_states = [state for state, record in self._states.items() if record.expires_at < now]
        for state in expired_states:
            self._states.pop(state, None)
