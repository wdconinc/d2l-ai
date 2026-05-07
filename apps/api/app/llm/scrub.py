from __future__ import annotations

import re

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
STUDENT_ID_PATTERN = re.compile(r"\b\d{7,}\b")


class PIIScrubber:
    """Redacts common PII patterns before provider invocation."""

    def scrub(self, text: str) -> str:
        scrubbed = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
        scrubbed = STUDENT_ID_PATTERN.sub("[REDACTED_ID]", scrubbed)
        return scrubbed
