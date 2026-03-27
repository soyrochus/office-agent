from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

FileType = Literal["docx", "pptx", "xlsx"]
OperationType = Literal["replace_text", "append_text", "write_value"]
SearchMode = Literal["keyword", "semantic", "hybrid"]
MatchMode = Literal["keyword", "semantic", "hybrid"]


@dataclass(frozen=True)
class DocumentRef:
    document_id: str
    path: Path
    file_type: FileType
    display_name: str
    modified_time: float
    content_hash: str | None = None
    item_count: int | None = None


@dataclass(frozen=True)
class ItemRef:
    document_id: str
    item_id: str
    item_type: str
    locator: str
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)
    content_text: str | None = None


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    item_id: str
    score: float
    matched_text: str
    locator: str
    item_type: str
    preview: str
    document_path: Path | None = None
    display_name: str | None = None
    match_mode: MatchMode | None = None
    scores: dict[str, float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexedItem:
    item_id: str
    item_type: str
    locator: str
    preview: str
    content_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class XlsxRowEmbeddingCell:
    item_id: str
    coordinate: str
    display_text: str
    preview: str


@dataclass(frozen=True)
class XlsxRowEmbedding:
    sheet_name: str
    row_number: int
    text: str
    preview: str
    representative_item_id: str
    contributing_cells: tuple[XlsxRowEmbeddingCell, ...]


@dataclass(frozen=True)
class PatchOperation:
    patch_id: str
    document_id: str
    item_id: str
    operation_type: OperationType
    payload: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    output_path: Path | None = None


@dataclass(frozen=True)
class StructureUnit:
    position: int
    unit_type: str
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentStructure:
    document: DocumentRef
    units: tuple[StructureUnit, ...]


@dataclass(frozen=True)
class PresentationSlideSummary:
    slide_number: int
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PresentationStructure:
    document: DocumentRef
    slides: tuple[PresentationSlideSummary, ...]


@dataclass(frozen=True)
class SlideTextBlock:
    position: int
    shape_id: int
    shape_name: str | None
    preview: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SlideBundle:
    document: DocumentRef
    slide_number: int
    preview: str
    notes_text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    text_blocks: tuple[SlideTextBlock, ...] = ()


@dataclass(frozen=True)
class SlideNotes:
    document_id: str
    slide_number: int
    notes_text: str


@dataclass(frozen=True)
class DocxParagraph:
    block_index: int
    paragraph_index: int
    text: str
    style_name: str | None
    is_heading: bool
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocxTable:
    block_index: int
    table_index: int
    rows: tuple[tuple[str, ...], ...]
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentBlock:
    block_index: int
    block_type: str
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentBlocks:
    document: DocumentRef
    blocks: tuple[DocumentBlock, ...]


@dataclass(frozen=True)
class ParagraphCollection:
    document: DocumentRef
    paragraphs: tuple[DocxParagraph, ...]


@dataclass(frozen=True)
class TableCollection:
    document: DocumentRef
    tables: tuple[DocxTable, ...]


@dataclass(frozen=True)
class BlockBundle:
    document: DocumentRef
    block: DocumentBlock
    paragraph: DocxParagraph | None = None
    table: DocxTable | None = None


@dataclass(frozen=True)
class WorksheetSummary:
    position: int
    sheet_name: str
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkbookStructure:
    document: DocumentRef
    sheets: tuple[WorksheetSummary, ...]


@dataclass(frozen=True)
class SheetCell:
    coordinate: str
    row: int
    column: int
    display_value: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SheetSnapshot:
    document: DocumentRef
    sheet_name: str
    cells: tuple[SheetCell, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructuredTarget:
    target_type: str
    identifier: str
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructuredWriteResult:
    document_path: Path
    output_path: Path
    target: StructuredTarget
    summary: str
