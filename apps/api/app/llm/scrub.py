from __future__ import annotations

import re

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
STUDENT_ID_PATTERN = re.compile(
    r"\b((?:student(?:\s*id)?|id)\s*[:#]?\s*)(\d{7,})\b",
    re.IGNORECASE,
)


class PIIScrubber:
    """Redacts common PII patterns before provider invocation."""

    def scrub(self, text: str) -> str:
        scrubbed = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
        scrubbed = STUDENT_ID_PATTERN.sub(r"\1[REDACTED_ID]", scrubbed)
        return scrubbed
