from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from offagent.app.services import IndexSummary, OutputMode, PatchResult
from offagent.domain.models import (
    BatchResult,
    ChildSummary,
    DocxRun,
    DocxTableCell,
    DocxTableEntry,
    DocxTablesResult,
    DocxParagraph,
    DocxTable,
    DocumentRef,
    FileType,
    InsertContentResult,
    ItemRef,
    MutationResult,
    NodePayload,
    NodeWriteResult,
    ObjectPayload,
    ParagraphCollection,
    PptxTextBlockNode,
    SearchHit,
    SearchMode,
    SectionPayload,
    StructureCollection,
    StructureSection,
    StructuredTarget,
    StructuredWriteResult,
    TableCollection,
    XlsxInsertRowsResult,
    XlsxSectionCell,
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
            scores=hit.scores,
            metadata=hit.metadata,
        )


class SearchObjectHitModel(MCPModel):
    document_id: str
    item_id: str
    score: float
    matched_text: str
    locator: str
    object_type: str
    preview: str
    document_path: str | None = None
    display_name: str | None = None
    match_mode: str | None = None
    scores: dict[str, float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_search_hit(cls, hit: SearchHit) -> "SearchObjectHitModel":
        return cls(
            document_id=hit.document_id,
            item_id=hit.item_id,
            score=hit.score,
            matched_text=hit.matched_text,
            locator=hit.locator,
            object_type=hit.item_type,
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


class SearchObjectsResult(MCPModel):
    hits: list[SearchObjectHitModel]

    @classmethod
    def from_hits(cls, hits: list[SearchHit]) -> "SearchObjectsResult":
        return cls(hits=[SearchObjectHitModel.from_search_hit(hit) for hit in hits])


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


class GetObjectRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class ListChildrenRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    child_type: str | None = None
    limit: int | None = Field(default=None, ge=1, le=1000)


class CreateObjectRequest(MCPModel):
    document_id: str = Field(min_length=1)
    parent_locator: str = Field(min_length=1)
    object_type: str = Field(min_length=1)
    properties: dict[str, Any] = Field(default_factory=dict)
    position: Any | None = None
    output_mode: OutputMode = "versioned"


class UpdateObjectRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    properties: dict[str, Any] = Field(default_factory=dict)
    output_mode: OutputMode = "versioned"


class MoveObjectRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    new_parent_locator: str = Field(min_length=1)
    position: Any | None = None
    output_mode: OutputMode = "versioned"


class CopyObjectRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    target_parent_locator: str = Field(min_length=1)
    position: Any | None = None
    output_mode: OutputMode = "versioned"


class BatchEditRequest(MCPModel):
    document_id: str = Field(min_length=1)
    operations: list[dict[str, Any]] = Field(min_length=1)
    output_mode: OutputMode = "versioned"
    dry_run: bool = False


class DeleteObjectRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    output_mode: OutputMode = "versioned"


class DocxSetParagraphStyleRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    style_name: str = Field(min_length=1)
    output_mode: OutputMode = "versioned"


class DocxInsertPageBreakRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    output_mode: OutputMode = "versioned"


class DocxAddTableRequest(MCPModel):
    document_id: str = Field(min_length=1)
    row_count: int = Field(ge=1)
    column_count: int = Field(ge=1)
    position: Any | None = None
    column_widths: list[int] | None = None
    style_name: str | None = None
    output_mode: OutputMode = "versioned"


class DocxMergeTableCellsRequest(MCPModel):
    document_id: str = Field(min_length=1)
    start_locator: str = Field(min_length=1)
    end_locator: str = Field(min_length=1)
    output_mode: OutputMode = "versioned"


class PptxAddSlideRequest(MCPModel):
    document_id: str = Field(min_length=1)
    layout_index: int | None = Field(default=None, ge=0)
    layout_name: str | None = None
    output_mode: OutputMode = "versioned"


class PptxDuplicateSlideRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    position: int | None = Field(default=None, ge=1)
    output_mode: OutputMode = "versioned"


class PptxSetSlideLayoutRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    layout_index: int | None = Field(default=None, ge=0)
    layout_name: str | None = None
    output_mode: OutputMode = "versioned"


class PptxAddTextShapeRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    text: str
    left: int
    top: int
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    output_mode: OutputMode = "versioned"


class XlsxWriteRangeRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    values: list[list[Any]] = Field(min_length=1)
    output_mode: OutputMode = "versioned"


class XlsxInsertColumnsRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    column_index: int = Field(ge=1)
    count: int = Field(ge=1)
    output_mode: OutputMode = "versioned"


class XlsxSetFormulaRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    formula: str = Field(min_length=1)
    output_mode: OutputMode = "versioned"


class XlsxMergeCellsRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    output_mode: OutputMode = "versioned"


class SemanticDocumentRequest(MCPModel):
    document_id: str = Field(min_length=1)


class SectionRequest(MCPModel):
    document_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    cell_range: str | None = None


class NodeRequest(MCPModel):
    document_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)


class WriteNodeRequest(MCPModel):
    document_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    content: str
    output_mode: OutputMode = "versioned"


class InsertContentRequest(MCPModel):
    document_id: str = Field(min_length=1)
    content: str
    style_name: str | None = None
    after_node_id: str | None = None
    output_mode: OutputMode = "versioned"


class XlsxInsertRowsRequest(MCPModel):
    document_id: str = Field(min_length=1)
    sheet_name: str | None = None
    rows: list[list[str]] | None = None
    records: list[dict[str, str]] | None = None
    locator: str | None = None
    row_number: int | None = Field(default=None, ge=1)
    count: int | None = Field(default=None, ge=1)
    output_mode: OutputMode = "versioned"


class StructureSectionModel(MCPModel):
    locator: str
    section_type: str
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    block_type: str | None = None
    slide_number: int | None = None
    sheet_name: str | None = None
    cell_count: int | None = None

    @classmethod
    def from_domain(cls, section: StructureSection) -> "StructureSectionModel":
        return cls(
            locator=section.locator,
            section_type=section.section_type,
            preview=section.preview,
            metadata=section.metadata,
            block_type=section.metadata.get("block_type"),
            slide_number=section.metadata.get("slide_number"),
            sheet_name=section.metadata.get("sheet_name"),
            cell_count=section.metadata.get("cell_count"),
        )


class GetStructureResult(MCPModel):
    document: DocumentModel
    sections: list[StructureSectionModel]

    @classmethod
    def from_domain(cls, result: StructureCollection) -> "GetStructureResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            sections=[StructureSectionModel.from_domain(section) for section in result.sections],
        )


class DocxRunModel(MCPModel):
    text: str
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    strike: bool | None = None
    font_name: str | None = None
    font_size: int | None = None
    color_rgb: str | None = None

    @classmethod
    def from_domain(cls, run: DocxRun) -> "DocxRunModel":
        return cls(**run.__dict__)


class DocxTableCellModel(MCPModel):
    locator: str
    row_index: int
    column_index: int
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, cell: DocxTableCell) -> "DocxTableCellModel":
        return cls(**cell.__dict__)


class PptxTextBlockNodeModel(MCPModel):
    locator: str
    position: int
    shape_id: int
    shape_name: str | None = None
    preview: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, block: PptxTextBlockNode) -> "PptxTextBlockNodeModel":
        return cls(**block.__dict__)


class XlsxSectionCellModel(MCPModel):
    locator: str
    coordinate: str
    row: int
    column: int
    display_value: str
    formula: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, cell: XlsxSectionCell) -> "XlsxSectionCellModel":
        return cls(**cell.__dict__)


class GetSectionResult(MCPModel):
    document: DocumentModel
    locator: str
    section_type: str
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    block_type: str | None = None
    text: str | None = None
    style_name: str | None = None
    is_heading: bool | None = None
    runs: list[DocxRunModel] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    table_cells: list[DocxTableCellModel] = Field(default_factory=list)
    slide_number: int | None = None
    notes_text: str | None = None
    text_blocks: list[PptxTextBlockNodeModel] = Field(default_factory=list)
    sheet_name: str | None = None
    cells: list[XlsxSectionCellModel] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, result: SectionPayload) -> "GetSectionResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            locator=result.locator,
            section_type=result.section_type,
            preview=result.preview,
            metadata=result.metadata,
            block_type=result.block_type,
            text=result.text,
            style_name=result.style_name,
            is_heading=result.is_heading,
            runs=[DocxRunModel.from_domain(run) for run in result.runs],
            rows=[list(row) for row in result.rows],
            table_cells=[DocxTableCellModel.from_domain(cell) for cell in result.table_cells],
            slide_number=result.slide_number,
            notes_text=result.notes_text,
            text_blocks=[PptxTextBlockNodeModel.from_domain(block) for block in result.text_blocks],
            sheet_name=result.sheet_name,
            cells=[XlsxSectionCellModel.from_domain(cell) for cell in result.cells],
        )


class ChildSummaryModel(MCPModel):
    locator: str
    object_type: str
    preview: str
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, result: ChildSummary) -> "ChildSummaryModel":
        return cls(
            locator=result.locator,
            object_type=result.object_type,
            preview=result.preview,
            capabilities=[capability.value for capability in result.capabilities],
            metadata=result.metadata,
        )


class GetObjectResult(MCPModel):
    document: DocumentModel
    locator: str
    object_type: str
    preview: str
    properties: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)
    parent_locator: str | None = None
    child_summary: list[ChildSummaryModel] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, result: ObjectPayload) -> "GetObjectResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            locator=result.locator,
            object_type=result.object_type,
            preview=result.preview,
            properties=result.properties,
            capabilities=[capability.value for capability in result.capabilities],
            parent_locator=result.parent_locator,
            child_summary=[ChildSummaryModel.from_domain(child) for child in result.child_summary],
            metadata=result.metadata,
        )


class ListChildrenResult(MCPModel):
    children: list[ChildSummaryModel]

    @classmethod
    def from_domain(cls, result: list[ChildSummary]) -> "ListChildrenResult":
        return cls(children=[ChildSummaryModel.from_domain(child) for child in result])


class GetNodeResult(MCPModel):
    document_id: str
    node_id: str
    item_type: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, result: NodePayload) -> "GetNodeResult":
        return cls(**result.__dict__)


class WriteNodeResult(MCPModel):
    document_id: str
    output_path: str
    node_id: str
    new_text: str
    previous_text: str

    @classmethod
    def from_domain(cls, result: NodeWriteResult) -> "WriteNodeResult":
        return cls(
            document_id=result.document_id,
            output_path=str(result.output_path),
            node_id=result.node_id,
            new_text=result.new_text,
            previous_text=result.previous_text,
        )


class InsertContentResultModel(MCPModel):
    document_id: str
    output_path: str
    new_node_id: str
    preview: str

    @classmethod
    def from_domain(cls, result: InsertContentResult) -> "InsertContentResultModel":
        return cls(
            document_id=result.document_id,
            output_path=str(result.output_path),
            new_node_id=result.new_node_id,
            preview=result.preview,
        )


class XlsxInsertRowsResultModel(MCPModel):
    document_id: str
    output_path: str
    rows_inserted: int | None = None
    first_row_locator: str | None = None
    locator: str | None = None
    object_type: str | None = None
    summary: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    parent_locator: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, result: XlsxInsertRowsResult) -> "XlsxInsertRowsResultModel":
        return cls(
            document_id=result.document_id,
            output_path=str(result.output_path),
            rows_inserted=result.rows_inserted,
            first_row_locator=result.first_row_locator,
        )

    @classmethod
    def from_mutation_result(cls, result: MutationResult) -> "XlsxInsertRowsResultModel":
        return cls(
            document_id=result.document_id,
            output_path="" if result.output_path is None else str(result.output_path),
            locator=result.locator,
            object_type=result.object_type,
            summary=result.summary,
            capabilities=[capability.value for capability in result.capabilities],
            parent_locator=result.parent_locator,
            metadata=result.metadata,
        )


class MutationResultModel(MCPModel):
    document_id: str
    output_path: str | None = None
    locator: str | None = None
    object_type: str
    summary: str
    capabilities: list[str] = Field(default_factory=list)
    parent_locator: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, result: MutationResult) -> "MutationResultModel":
        return cls(
            document_id=result.document_id,
            output_path=None if result.output_path is None else str(result.output_path),
            locator=result.locator,
            object_type=result.object_type,
            summary=result.summary,
            capabilities=[capability.value for capability in result.capabilities],
            parent_locator=result.parent_locator,
            metadata=result.metadata,
        )


class BatchResultModel(MCPModel):
    document_id: str
    output_path: str | None = None
    summary: str
    dry_run: bool = False
    operations: list[MutationResultModel] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, result: BatchResult) -> "BatchResultModel":
        return cls(
            document_id=result.document_id,
            output_path=None if result.output_path is None else str(result.output_path),
            summary=result.summary,
            dry_run=result.dry_run,
            operations=[MutationResultModel.from_domain(operation) for operation in result.operations],
            metadata=result.metadata,
        )


class DocxTableEntryModel(MCPModel):
    locator: str
    table_index: int
    rows: list[list[str]]
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, result: DocxTableEntry) -> "DocxTableEntryModel":
        return cls(
            locator=result.locator,
            table_index=result.table_index,
            rows=[list(row) for row in result.rows],
            preview=result.preview,
            metadata=result.metadata,
        )


class DocxGetTablesResult(MCPModel):
    document: DocumentModel
    tables: list[DocxTableEntryModel]

    @classmethod
    def from_domain(cls, result: DocxTablesResult) -> "DocxGetTablesResult":
        return cls(
            document=DocumentModel.from_document_ref(result.document),
            tables=[DocxTableEntryModel.from_domain(table) for table in result.tables],
        )
