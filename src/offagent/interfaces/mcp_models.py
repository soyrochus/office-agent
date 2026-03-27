from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from offagent.app.services import IndexSummary, OutputMode, PatchResult
from offagent.domain.models import (
    BlockBundle,
    DocxParagraph,
    DocxTable,
    DocumentBlock,
    DocumentBlocks,
    DocumentRef,
    DocumentStructure,
    FileType,
    ItemRef,
    ParagraphCollection,
    PresentationSlideSummary,
    PresentationStructure,
    SearchHit,
    SearchMode,
    SheetCell,
    SheetSnapshot,
    SlideBundle,
    SlideNotes,
    SlideTextBlock,
    StructureUnit,
    StructuredTarget,
    StructuredWriteResult,
    TableCollection,
    WorkbookStructure,
    WorksheetSummary,
)


class MCPModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentModel(MCPModel):
    document_id: str
    path: str
    file_type: FileType
    display_name: str
    modified_time: float
    content_hash: str | None = None
    item_count: int | None = None

    @classmethod
    def from_document_ref(cls, document: DocumentRef) -> "DocumentModel":
        return cls(
            document_id=document.document_id,
            path=str(document.path),
            file_type=document.file_type,
            display_name=document.display_name,
            modified_time=document.modified_time,
            content_hash=document.content_hash,
            item_count=document.item_count,
        )


class ItemModel(MCPModel):
    document_id: str
    item_id: str
    item_type: str
    locator: str
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_item_ref(cls, item: ItemRef) -> "ItemModel":
        return cls(
            document_id=item.document_id,
            item_id=item.item_id,
            item_type=item.item_type,
            locator=item.locator,
            preview=item.preview,
            metadata=item.metadata,
        )


class SearchHitModel(MCPModel):
    document_id: str
    item_id: str
    score: float
    matched_text: str
    locator: str
    item_type: str
    preview: str
    document_path: str | None = None
    display_name: str | None = None
    match_mode: str | None = None
    scores: dict[str, float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_search_hit(cls, hit: SearchHit) -> "SearchHitModel":
        return cls(
            document_id=hit.document_id,
            item_id=hit.item_id,
            score=hit.score,
            matched_text=hit.matched_text,
            locator=hit.locator,
            item_type=hit.item_type,
            preview=hit.preview,
            document_path=None if hit.document_path is None else str(hit.document_path),
            display_name=hit.display_name,
            match_mode=hit.match_mode,
            scores=hit.scores,
            metadata=hit.metadata,
        )


class IndexPathResult(MCPModel):
    path: str
    files_scanned: int
    files_indexed: int
    files_skipped: int

    @classmethod
    def from_index_summary(cls, path: Path, summary: IndexSummary) -> "IndexPathResult":
        return cls(
            path=str(path),
            files_scanned=summary.files_scanned,
            files_indexed=summary.files_indexed,
            files_skipped=summary.files_skipped,
        )


class IndexDocumentsResult(MCPModel):
    files_scanned: int
    files_indexed: int
    files_skipped: int
    results: list[IndexPathResult]

    @classmethod
    def from_results(cls, results: list[IndexPathResult]) -> "IndexDocumentsResult":
        return cls(
            files_scanned=sum(result.files_scanned for result in results),
            files_indexed=sum(result.files_indexed for result in results),
            files_skipped=sum(result.files_skipped for result in results),
            results=results,
        )


class RefreshDocumentResult(MCPModel):
    document: DocumentModel
    files_scanned: int
    files_indexed: int
    files_skipped: int

    @classmethod
    def from_refresh(cls, document: DocumentRef, summary: IndexSummary) -> "RefreshDocumentResult":
        return cls(
            document=DocumentModel.from_document_ref(document),
            files_scanned=summary.files_scanned,
            files_indexed=summary.files_indexed,
            files_skipped=summary.files_skipped,
        )


class ListDocumentsResult(MCPModel):
    documents: list[DocumentModel]

    @classmethod
    def from_documents(cls, documents: list[DocumentRef]) -> "ListDocumentsResult":
        return cls(documents=[DocumentModel.from_document_ref(document) for document in documents])


class SearchDocumentsResult(MCPModel):
    hits: list[SearchHitModel]

    @classmethod
    def from_hits(cls, hits: list[SearchHit]) -> "SearchDocumentsResult":
        return cls(hits=[SearchHitModel.from_search_hit(hit) for hit in hits])


class LocateItemResult(MCPModel):
    item: ItemModel

    @classmethod
    def from_item(cls, item: ItemRef) -> "LocateItemResult":
        return cls(item=ItemModel.from_item_ref(item))


class ReadItemResult(MCPModel):
    document_id: str
    item_id: str
    text: str


class WriteResult(MCPModel):
    document_path: str
    output_path: str
    item: ItemModel
    text: str

    @classmethod
    def from_patch_result(cls, result: PatchResult) -> "WriteResult":
        return cls(
            document_path=str(result.document_path),
            output_path=str(result.output_path),
            item=ItemModel.from_item_ref(result.item),
            text=result.text,
        )


class IndexDocumentsRequest(MCPModel):
    paths: list[str] = Field(min_length=1)


class RefreshDocumentRequest(MCPModel):
    document_id: str = Field(min_length=1)


class SearchDocumentsRequest(MCPModel):
    query: str = Field(min_length=1)
    file_type: FileType | None = None
    document_id: str | None = None
    mode: SearchMode = "keyword"
    limit: int = Field(default=20, ge=1, le=100)


class LocateItemRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class ReadItemRequest(MCPModel):
    document_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)


class ReplaceTextRequest(MCPModel):
    document_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    new_text: str
    output_mode: OutputMode = "versioned"


class StructureUnitModel(MCPModel):
    position: int
    unit_type: str
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, unit: StructureUnit) -> "StructureUnitModel":
        return cls(
            position=unit.position,
            unit_type=unit.unit_type,
            preview=unit.preview,
            metadata=unit.metadata,
        )


class DocumentStructureResult(MCPModel):
    document: DocumentModel
    units: list[StructureUnitModel]

    @classmethod
    def from_domain(cls, result: DocumentStructure) -> "DocumentStructureResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            units=[StructureUnitModel.from_domain(unit) for unit in result.units],
        )


class PresentationSlideSummaryModel(MCPModel):
    slide_number: int
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, slide: PresentationSlideSummary) -> "PresentationSlideSummaryModel":
        return cls(slide_number=slide.slide_number, preview=slide.preview, metadata=slide.metadata)


class PresentationStructureResult(MCPModel):
    document: DocumentModel
    slides: list[PresentationSlideSummaryModel]

    @classmethod
    def from_domain(cls, result: PresentationStructure) -> "PresentationStructureResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            slides=[PresentationSlideSummaryModel.from_domain(slide) for slide in result.slides],
        )


class SlideTextBlockModel(MCPModel):
    position: int
    shape_id: int
    shape_name: str | None = None
    preview: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, block: SlideTextBlock) -> "SlideTextBlockModel":
        return cls(
            position=block.position,
            shape_id=block.shape_id,
            shape_name=block.shape_name,
            preview=block.preview,
            text=block.text,
            metadata=block.metadata,
        )


class SlideBundleResult(MCPModel):
    document: DocumentModel
    slide_number: int
    preview: str
    notes_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    text_blocks: list[SlideTextBlockModel]

    @classmethod
    def from_domain(cls, result: SlideBundle) -> "SlideBundleResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            slide_number=result.slide_number,
            preview=result.preview,
            notes_text=result.notes_text,
            metadata=result.metadata,
            text_blocks=[SlideTextBlockModel.from_domain(block) for block in result.text_blocks],
        )


class SlideNotesResult(MCPModel):
    document_id: str
    slide_number: int
    notes_text: str

    @classmethod
    def from_domain(cls, result: SlideNotes) -> "SlideNotesResult":
        return cls(
            document_id=result.document_id,
            slide_number=result.slide_number,
            notes_text=result.notes_text,
        )


class WorksheetSummaryModel(MCPModel):
    position: int
    sheet_name: str
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, sheet: WorksheetSummary) -> "WorksheetSummaryModel":
        return cls(
            position=sheet.position,
            sheet_name=sheet.sheet_name,
            preview=sheet.preview,
            metadata=sheet.metadata,
        )


class WorkbookStructureResult(MCPModel):
    document: DocumentModel
    sheets: list[WorksheetSummaryModel]

    @classmethod
    def from_domain(cls, result: WorkbookStructure) -> "WorkbookStructureResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            sheets=[WorksheetSummaryModel.from_domain(sheet) for sheet in result.sheets],
        )


class SheetCellModel(MCPModel):
    coordinate: str
    row: int
    column: int
    display_value: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, cell: SheetCell) -> "SheetCellModel":
        return cls(
            coordinate=cell.coordinate,
            row=cell.row,
            column=cell.column,
            display_value=cell.display_value,
            metadata=cell.metadata,
        )


class SheetSnapshotResult(MCPModel):
    document: DocumentModel
    sheet_name: str
    cells: list[SheetCellModel]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, result: SheetSnapshot) -> "SheetSnapshotResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            sheet_name=result.sheet_name,
            cells=[SheetCellModel.from_domain(cell) for cell in result.cells],
            metadata=result.metadata,
        )


class DocumentBlockModel(MCPModel):
    block_index: int
    block_type: str
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, block: DocumentBlock) -> "DocumentBlockModel":
        return cls(
            block_index=block.block_index,
            block_type=block.block_type,
            preview=block.preview,
            metadata=block.metadata,
        )


class DocumentBlocksResult(MCPModel):
    document: DocumentModel
    blocks: list[DocumentBlockModel]

    @classmethod
    def from_domain(cls, result: DocumentBlocks) -> "DocumentBlocksResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            blocks=[DocumentBlockModel.from_domain(block) for block in result.blocks],
        )


class DocxParagraphModel(MCPModel):
    block_index: int
    paragraph_index: int
    text: str
    style_name: str | None = None
    is_heading: bool
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, paragraph: DocxParagraph) -> "DocxParagraphModel":
        return cls(
            block_index=paragraph.block_index,
            paragraph_index=paragraph.paragraph_index,
            text=paragraph.text,
            style_name=paragraph.style_name,
            is_heading=paragraph.is_heading,
            preview=paragraph.preview,
            metadata=paragraph.metadata,
        )


class ParagraphsResult(MCPModel):
    document: DocumentModel
    paragraphs: list[DocxParagraphModel]

    @classmethod
    def from_domain(cls, result: ParagraphCollection) -> "ParagraphsResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            paragraphs=[DocxParagraphModel.from_domain(paragraph) for paragraph in result.paragraphs],
        )


class DocxTableModel(MCPModel):
    block_index: int
    table_index: int
    rows: list[list[str]]
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, table: DocxTable) -> "DocxTableModel":
        return cls(
            block_index=table.block_index,
            table_index=table.table_index,
            rows=[list(row) for row in table.rows],
            preview=table.preview,
            metadata=table.metadata,
        )


class TablesResult(MCPModel):
    document: DocumentModel
    tables: list[DocxTableModel]

    @classmethod
    def from_domain(cls, result: TableCollection) -> "TablesResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            tables=[DocxTableModel.from_domain(table) for table in result.tables],
        )


class BlockBundleResult(MCPModel):
    document: DocumentModel
    block: DocumentBlockModel
    paragraph: DocxParagraphModel | None = None
    table: DocxTableModel | None = None

    @classmethod
    def from_domain(cls, result: BlockBundle) -> "BlockBundleResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            block=DocumentBlockModel.from_domain(result.block),
            paragraph=(
                None if result.paragraph is None else DocxParagraphModel.from_domain(result.paragraph)
            ),
            table=None if result.table is None else DocxTableModel.from_domain(result.table),
        )


class StructuredTargetModel(MCPModel):
    target_type: str
    identifier: str
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, target: StructuredTarget) -> "StructuredTargetModel":
        return cls(
            target_type=target.target_type,
            identifier=target.identifier,
            preview=target.preview,
            metadata=target.metadata,
        )


class StructuredWriteToolResult(MCPModel):
    document_path: str
    output_path: str
    target: StructuredTargetModel
    summary: str

    @classmethod
    def from_domain(cls, result: StructuredWriteResult) -> "StructuredWriteToolResult":
        return cls(
            document_path=str(result.document_path),
            output_path=str(result.output_path),
            target=StructuredTargetModel.from_domain(result.target),
            summary=result.summary,
        )


class SemanticDocumentRequest(MCPModel):
    document_id: str = Field(min_length=1)


class SlideRequest(MCPModel):
    document_id: str = Field(min_length=1)
    slide_number: int = Field(ge=1)


class SheetSnapshotRequest(MCPModel):
    document_id: str = Field(min_length=1)
    sheet_name: str = Field(min_length=1)
    cell_range: str | None = None
    start_cell: str | None = None
    row_count: int | None = Field(default=None, ge=1)
    column_count: int | None = Field(default=None, ge=1)


class BlockRequest(MCPModel):
    document_id: str = Field(min_length=1)
    block_index: int = Field(ge=0)


class AppendRowRequest(MCPModel):
    document_id: str = Field(min_length=1)
    sheet_name: str = Field(min_length=1)
    values: list[str] | None = None
    record: dict[str, str] | None = None
    output_mode: OutputMode = "versioned"


class WriteTableRequest(MCPModel):
    document_id: str = Field(min_length=1)
    sheet_name: str = Field(min_length=1)
    rows: list[list[str]] | None = None
    records: list[dict[str, str]] | None = None
    column_mapping: dict[str, str] | None = None
    output_mode: OutputMode = "versioned"


class AppendParagraphRequest(MCPModel):
    document_id: str = Field(min_length=1)
    text: str
    style_name: str | None = None
    output_mode: OutputMode = "versioned"


class ReplaceBlockRequest(MCPModel):
    document_id: str = Field(min_length=1)
    block_index: int = Field(ge=0)
    text: str
    output_mode: OutputMode = "versioned"


class AppendTextRequest(MCPModel):
    document_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    text_to_add: str
    output_mode: OutputMode = "versioned"


class WriteCellRequest(MCPModel):
    document_id: str = Field(min_length=1)
    sheet: str = Field(min_length=1)
    cell: str = Field(min_length=1)
    value: str
    output_mode: OutputMode = "versioned"
