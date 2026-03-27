from __future__ import annotations

from offagent.domain.models import (
    BlockBundle,
    DocumentBlocks,
    DocumentStructure,
    ParagraphCollection,
    PresentationStructure,
    SheetSnapshot,
    SlideBundle,
    SlideNotes,
    StructuredWriteResult,
    TableCollection,
    WorkbookStructure,
)
from offagent.interfaces.mcp_models import (
    BlockBundleResult,
    DocumentBlocksResult,
    DocumentStructureResult,
    ParagraphsResult,
    PresentationStructureResult,
    SheetSnapshotResult,
    SlideBundleResult,
    SlideNotesResult,
    StructuredWriteToolResult,
    TablesResult,
    WorkbookStructureResult,
)


def convert_document_structure(result: DocumentStructure) -> DocumentStructureResult:
    return DocumentStructureResult.from_domain(result)


def convert_presentation_structure(result: PresentationStructure) -> PresentationStructureResult:
    return PresentationStructureResult.from_domain(result)


def convert_slide_bundle(result: SlideBundle) -> SlideBundleResult:
    return SlideBundleResult.from_domain(result)


def convert_slide_notes(result: SlideNotes) -> SlideNotesResult:
    return SlideNotesResult.from_domain(result)


def convert_workbook_structure(result: WorkbookStructure) -> WorkbookStructureResult:
    return WorkbookStructureResult.from_domain(result)


def convert_sheet_snapshot(result: SheetSnapshot) -> SheetSnapshotResult:
    return SheetSnapshotResult.from_domain(result)


def convert_document_blocks(result: DocumentBlocks) -> DocumentBlocksResult:
    return DocumentBlocksResult.from_domain(result)


def convert_paragraphs(result: ParagraphCollection) -> ParagraphsResult:
    return ParagraphsResult.from_domain(result)


def convert_tables(result: TableCollection) -> TablesResult:
    return TablesResult.from_domain(result)


def convert_block_bundle(result: BlockBundle) -> BlockBundleResult:
    return BlockBundleResult.from_domain(result)


def convert_structured_write_result(result: StructuredWriteResult) -> StructuredWriteToolResult:
    return StructuredWriteToolResult.from_domain(result)
