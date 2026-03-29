from __future__ import annotations

from pathlib import Path
from typing import Protocol

from offagent.domain.models import Capability, ChildSummary, ObjectPayload


class ObjectResolver(Protocol):
    def get_object(self, document_path: Path, locator: str) -> ObjectPayload:
        """Resolve a single object by locator."""

    def list_children(
        self,
        document_path: Path,
        locator: str,
        *,
        child_type: str | None = None,
        limit: int | None = None,
    ) -> list[ChildSummary]:
        """Return ordered child objects for a container locator."""

    def resolve_capabilities(
        self, document_path: Path, locator: str
    ) -> frozenset[Capability]:
        """Compute live capabilities for a locator."""
