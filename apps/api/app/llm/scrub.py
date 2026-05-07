from __future__ import annotations

import re

_STUDENT_ID_RE = re.compile(r"\b\d{7}\b")


def scrub_prompt_text(text: str) -> str:
    """Redact obvious student identifier patterns before LLM use."""
    return _STUDENT_ID_RE.sub("[REDACTED_STUDENT_ID]", text)
