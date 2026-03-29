from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

FileType = Literal["docx", "pptx", "xlsx"]
OperationType = Literal["replace_text", "append_text", "write_value"]
SearchMode = Literal["keyword", "semantic", "hybrid"]
MatchMode = Literal["keyword", "semantic", "hybrid"]


class Capability(StrEnum):
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ADD_CHILD = "add_child"
    MOVE = "move"
    COPY = "copy"
    STYLE = "style"


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


@dataclass(frozen=True)
class StructureSection:
    locator: str
    section_type: str
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructureCollection:
    document: DocumentRef
    sections: tuple[StructureSection, ...]


@dataclass(frozen=True)
class DocxRun:
    text: str
    bold: bool | None
    italic: bool | None
    underline: bool | None
    strike: bool | None
    font_name: str | None
    font_size: int | None
    color_rgb: str | None


@dataclass(frozen=True)
class DocxTableCell:
    locator: str
    row_index: int
    column_index: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PptxTextBlockNode:
    locator: str
    position: int
    shape_id: int
    shape_name: str | None
    preview: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class XlsxSectionCell:
    locator: str
    coordinate: str
    row: int
    column: int
    display_value: str
    formula: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SectionPayload:
    document: DocumentRef
    locator: str
    section_type: str
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)
    block_type: str | None = None
    text: str | None = None
    style_name: str | None = None
    is_heading: bool | None = None
    runs: tuple[DocxRun, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    table_cells: tuple[DocxTableCell, ...] = ()
    slide_number: int | None = None
    notes_text: str | None = None
    text_blocks: tuple[PptxTextBlockNode, ...] = ()
    sheet_name: str | None = None
    cells: tuple[XlsxSectionCell, ...] = ()


@dataclass(frozen=True)
class NodePayload:
    document_id: str
    node_id: str
    item_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NodeWriteResult:
    document_path: Path
    output_path: Path
    document_id: str
    node_id: str
    new_text: str
    previous_text: str


@dataclass(frozen=True)
class InsertContentResult:
    document_path: Path
    output_path: Path
    document_id: str
    new_node_id: str
    preview: str


@dataclass(frozen=True)
class XlsxInsertRowsResult:
    document_path: Path
    output_path: Path
    document_id: str
    rows_inserted: int
    first_row_locator: str


@dataclass(frozen=True)
class DocxTableEntry:
    locator: str
    table_index: int
    rows: tuple[tuple[str, ...], ...]
    preview: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocxTablesResult:
    document: DocumentRef
    tables: tuple[DocxTableEntry, ...]


@dataclass(frozen=True)
class ChildSummary:
    locator: str
    object_type: str
    preview: str
    capabilities: tuple[Capability, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObjectPayload:
    document: DocumentRef
    locator: str
    object_type: str
    preview: str
    properties: dict[str, Any] = field(default_factory=dict)
    capabilities: tuple[Capability, ...] = ()
    parent_locator: str | None = None
    child_summary: tuple[ChildSummary, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MutationResult:
    document_path: Path
    output_path: Path | None
    document_id: str
    locator: str | None
    object_type: str
    summary: str
    capabilities: tuple[Capability, ...] = ()
    parent_locator: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchResult:
    document_path: Path
    output_path: Path | None
    document_id: str
    summary: str
    dry_run: bool = False
    operations: tuple[MutationResult, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
