"""Retry helpers for transient Brightspace API failures."""

from __future__ import annotations

from collections.abc import Callable
from time import sleep as default_sleep


def retry_with_exponential_backoff(
    operation: Callable[[], object],
    should_retry: Callable[[object], bool],
    *,
    max_attempts: int = 4,
    base_delay_seconds: float = 0.25,
    sleep: Callable[[float], None] = default_sleep,
) -> object:
    """Run an operation and retry with exponential backoff when requested."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    for attempt in range(max_attempts):
        result = operation()
        if not should_retry(result) or attempt == max_attempts - 1:
            return result
        sleep(base_delay_seconds * (2**attempt))

    return operation()
