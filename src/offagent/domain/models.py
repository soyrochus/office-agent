from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

FileType = Literal["docx", "pptx", "xlsx"]
OperationType = Literal["replace_text", "append_text", "write_value"]


@dataclass(frozen=True)
class DocumentRef:
    document_id: str
    path: Path
    file_type: FileType
    display_name: str
    modified_time: float
    content_hash: str | None = None


@dataclass(frozen=True)
class ItemRef:
    document_id: str
    item_id: str
    item_type: str
    locator: str
    preview: str


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    item_id: str
    score: float
    matched_text: str
    locator: str
    item_type: str
    preview: str


@dataclass(frozen=True)
class PatchOperation:
    patch_id: str
    document_id: str
    item_id: str
    operation_type: OperationType
    payload: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    output_path: Path | None = None
