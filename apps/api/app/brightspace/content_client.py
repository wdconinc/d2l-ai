from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class ModuleTopic:
    id: int
    title: str
    topic_type: str
    content: str


class BrightspaceContentClient(Protocol):
    async def list_module_topics(self, org_unit_id: int, module_id: int) -> Sequence[ModuleTopic]:
        """Return topics for a module from Brightspace LE content endpoints."""
