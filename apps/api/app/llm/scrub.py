from __future__ import annotations

import re

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
STUDENT_ID_PATTERN = re.compile(
    r"(?im)\b((?:student\s*id|d2l\s*id|user\s*id|userid|student\s*number|id)\s*[:=#-]?\s*)(\d{6,12})\b"
)
NAME_FIELD_PATTERN = re.compile(
    r"(?im)\b("
    r"student\s*name|full\s*name|display\s*name|"
    r"givenname|familyname|firstname|lastname|"
    r"nom|pr(?:é|e)nom|nom\s+de\s+famille"
    r")\s*[:=]\s*([^\n,;]+)"
)


class PIIScrubber:
    """Redacts common PII patterns before provider invocation."""

    def scrub(self, text: str) -> str:
        scrubbed = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
        scrubbed = STUDENT_ID_PATTERN.sub(r"\1[REDACTED_ID]", scrubbed)
        return NAME_FIELD_PATTERN.sub(r"\1: [REDACTED_NAME]", scrubbed)


def scrub_prompt_text(text: str) -> str:
    """Backward-compatible helper for direct prompt scrubbing."""
    return PIIScrubber().scrub(text)
