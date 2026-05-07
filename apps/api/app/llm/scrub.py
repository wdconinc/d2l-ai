from __future__ import annotations

import re

_STUDENT_ID_RE = re.compile(r"\b\d{7}\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_NAME_FIELD_RE = re.compile(
    r"(?im)\b(student\s*name|name|givenname|familyname|firstname|lastname)\s*[:=]\s*([^\n,;]+)"
)


def scrub_prompt_text(text: str) -> str:
    """Redact obvious student identifier patterns before LLM use."""
    scrubbed = _STUDENT_ID_RE.sub("[REDACTED_STUDENT_ID]", text)
    scrubbed = _EMAIL_RE.sub("[REDACTED_EMAIL]", scrubbed)
    return _NAME_FIELD_RE.sub(r"\1: [REDACTED_NAME]", scrubbed)
