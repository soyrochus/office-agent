from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, TypeVar

from offagent.adapters import pptx_adapter, xlsx_adapter
from offagent.app.services import AppServices
from offagent.config import AppConfig
from offagent.errors import (
    InvalidArgumentsError,
    PolicyRefusedError,
    StaleLocatorError,
    TargetNotEditableError,
    TargetNotFoundError,
)
from offagent.interfaces import mcp_converters
from offagent.interfaces.mcp_models import (
    AddContentBlockRequest,
    BatchEditRequest,
    BatchResultModel,
    CopyObjectRequest,
    CreateDocumentRequest,
    CreateObjectRequest,
    DeleteObjectRequest,
    BlockStyleModel,
    DocxAddTableRequest,
    DocxGetTablesResult,
    DocxInsertPageBreakRequest,
    DocxMergeTableCellsRequest,
    DocxSetParagraphStyleRequest,
    GetObjectRequest,
    GetObjectResult,
    GetNodeResult,
    GetSectionResult,
    GetStructureResult,
    IndexDocumentsRequest,
    IndexDocumentsResult,
    IndexPathResult,
    InsertContentRequest,
    InsertContentResultModel,
    ListChildrenRequest,
    ListChildrenResult,
    ListDocumentsResult,
    MoveObjectRequest,
    MutationResultModel,
    NodeRequest,
    PptxAddSlideRequest,
    PptxAddTextShapeRequest,
    PptxDuplicateSlideRequest,
    PptxSetSlideLayoutRequest,
    RefreshDocumentRequest,
    RefreshDocumentResult,
    SearchDocumentsRequest,
    SearchDocumentsResult,
    SearchObjectsResult,
    SectionRequest,
    SemanticDocumentRequest,
    SetStructuralRoleRequest,
    StyleBlockRequest,
    StyleInlineRequest,
    UpdateObjectRequest,
    WriteNodeRequest,
    WriteNodeResult,
    XlsxInsertColumnsRequest,
    XlsxInsertRowsRequest,
    XlsxInsertRowsResultModel,
    XlsxMergeCellsRequest,
    XlsxSetFormulaRequest,
    XlsxWriteRangeRequest,
)

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.exceptions import ToolError
except ModuleNotFoundError:  # pragma: no cover - exercised when MCP dependency is absent
    FastMCP = None
    ToolError = None

LOGGER = logging.getLogger(__name__)

EXPECTED_TOOL_ERRORS = (
    FileNotFoundError,
    InvalidArgumentsError,
    TargetNotFoundError,
    TargetNotEditableError,
    PolicyRefusedError,
    StaleLocatorError,
    RuntimeError,
    pptx_adapter.TargetNotEditableError,
    xlsx_adapter.TargetNotAppendableError,
)

SERVER_INSTRUCTIONS = (
    "Office Agent exposes MCP tools for Office document workflows. "
    "Use `get_structure` to navigate a document, `get_section` to inspect one section, "
    "`get_object` and `list_children` for typed object traversal, and `get_node` or `write_node` "
    "for leaf-node reads and writes. Any locator returned by search or structure tools is valid in object "
    "and node tools "
    "for the same document version. Format-specific tools include `insert_content`, "
    "`docx_get_tables`, DOCX/PPTX/XLSX escape hatches, and the overloaded `xlsx_insert_rows` tool. "
    "`search_objects` is the canonical V2 search tool; `search_documents` remains as a deprecated compatibility alias."
)

T = TypeVar("T")


def build_mcp_server(config: AppConfig):
    if FastMCP is None or ToolError is None:
        raise RuntimeError("The MCP Python SDK is required to run `office-agent mcp`.")

    services = AppServices(config)
    mcp = FastMCP("Office Agent", instructions=SERVER_INSTRUCTIONS, json_response=True)

    @mcp.tool(description="Index one or more Office document paths or directories.")
    def index_documents(paths: list[str]) -> IndexDocumentsResult:
        request = IndexDocumentsRequest.model_validate({"paths": paths})

        def runner() -> IndexDocumentsResult:
            results: list[IndexPathResult] = []
            for raw_path in request.paths:
                path = Path(raw_path).expanduser()
                summary = services.index_path(path)
                results.append(IndexPathResult.from_index_summary(path.resolve(), summary))
            return IndexDocumentsResult.from_results(results)

        return _run_tool(runner)

    @mcp.tool(description="Refresh an indexed document by document id.")
    def refresh_document(document_id: str) -> RefreshDocumentResult:
        request = RefreshDocumentRequest.model_validate({"document_id": document_id})

        def runner() -> RefreshDocumentResult:
            summary = services.refresh_document(request.document_id)
            document = services.get_document(request.document_id)
            return RefreshDocumentResult.from_refresh(document, summary)

        return _run_tool(runner)

    @mcp.tool(description="List indexed documents known to Office Agent.")
    def list_documents() -> ListDocumentsResult:
        return _run_tool(lambda: ListDocumentsResult.from_documents(services.list_documents()))

    @mcp.tool(description="Deprecated alias for `search_objects` that preserves the pre-V2 response shape.")
    def search_documents(
        query: str,
        file_type: str | None = None,
        document_id: str | None = None,
        mode: str = "keyword",
        limit: int = 20,
    ) -> SearchDocumentsResult:
        request = SearchDocumentsRequest.model_validate(
            {
                "query": query,
                "file_type": file_type,
                "document_id": document_id,
                "mode": mode,
                "limit": limit,
            }
        )

        def runner() -> SearchDocumentsResult:
            document_path = None
            if request.document_id is not None:
                document_path = services.resolve_document_path(request.document_id)
            hits = services.search_corpus(
                request.query,
                file_type=request.file_type,
                document_path=document_path,
                limit=request.limit,
                mode=request.mode,
            )
            return SearchDocumentsResult.from_hits(hits)

        return _run_tool(runner)

    @mcp.tool(description="Return the top-level structure for an indexed Office document.")
    def get_structure(document_id: str) -> GetStructureResult:
        request = SemanticDocumentRequest.model_validate({"document_id": document_id})
        return _run_tool(
            lambda: mcp_converters.convert_get_structure(
                services.get_structure(request.document_id)
            )
        )

    @mcp.tool(description="Return the full structured payload for one document section.")
    def get_section(
        document_id: str,
        section_id: str,
        cell_range: str | None = None,
    ) -> GetSectionResult:
        request = SectionRequest.model_validate(
            {
                "document_id": document_id,
                "section_id": section_id,
                "cell_range": cell_range,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_get_section(
                services.get_section(
                    request.document_id,
                    request.section_id,
                    cell_range=request.cell_range,
                )
            )
        )

    @mcp.tool(description="Read the current content for a single node locator.")
    def get_node(document_id: str, node_id: str) -> GetNodeResult:
        request = NodeRequest.model_validate({"document_id": document_id, "node_id": node_id})
        return _run_tool(
            lambda: mcp_converters.convert_get_node(
                services.get_node(request.document_id, request.node_id)
            )
        )

    @mcp.tool(description="Replace content at a single node locator and re-index the output document.")
    def write_node(
        document_id: str,
        node_id: str,
        content: str,
        output_mode: str = "versioned",
    ) -> WriteNodeResult:
        request = WriteNodeRequest.model_validate(
            {
                "document_id": document_id,
                "node_id": node_id,
                "content": content,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_write_node(
                services.write_node(
                    request.document_id,
                    request.node_id,
                    request.content,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Insert a new DOCX paragraph, optionally after an existing locator.")
    def insert_content(
        document_id: str,
        content: str,
        style_name: str | None = None,
        after_node_id: str | None = None,
        output_mode: str = "versioned",
    ) -> InsertContentResultModel:
        request = InsertContentRequest.model_validate(
            {
                "document_id": document_id,
                "content": content,
                "style_name": style_name,
                "after_node_id": after_node_id,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_insert_content(
                services.insert_content(
                    request.document_id,
                    request.content,
                    style_name=request.style_name,
                    after_node_id=request.after_node_id,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Create a new empty DOCX, PPTX, or XLSX document and index it immediately.")
    def create_document(
        format: str,
        output_path: str,
        initial_sheet_name: str | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = CreateDocumentRequest.model_validate(
            {
                "format": format,
                "output_path": output_path,
                "initial_sheet_name": initial_sheet_name,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.create_document(
                    request.format,
                    Path(request.output_path).expanduser(),
                    initial_sheet_name=request.initial_sheet_name,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Add a format-specific content block to an existing Office document.")
    def add_content_block(
        document_id: str,
        block_type: str,
        properties: dict,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = AddContentBlockRequest.model_validate(
            {
                "document_id": document_id,
                "block_type": block_type,
                "properties": properties,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.add_content_block(
                    request.document_id,
                    request.block_type,
                    request.properties,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Apply inline font styling to a DOCX run, PPTX text run, or XLSX cell.")
    def style_inline(
        document_id: str,
        locator: str,
        style: dict,
        range: dict | None = None,
        clear_fields: list[str] | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = StyleInlineRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "style": style,
                "range": range,
                "clear_fields": clear_fields or [],
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.style_inline(
                    request.document_id,
                    request.locator,
                    request.style.to_domain(),
                    request.clear_fields,
                    text_range=None if request.range is None else request.range.to_domain(),
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Apply block-level styling to a DOCX paragraph, PPTX paragraph, or XLSX cell.")
    def style_block(
        document_id: str,
        locator: str,
        style: dict,
        clear_fields: list[str] | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = StyleBlockRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "style": style,
                "clear_fields": clear_fields or [],
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.style_block(
                    request.document_id,
                    request.locator,
                    request.style.to_domain(),
                    request.clear_fields,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Apply a DOCX structural role using standard Word paragraph styles.")
    def set_structural_role(
        document_id: str,
        locator: str,
        role: str,
        level: int | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = SetStructuralRoleRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "role": role,
                "level": level,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.set_structural_role(
                    request.document_id,
                    request.locator,
                    request.role,
                    level=request.level,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Return all DOCX tables with locators that can be passed to get_section.")
    def docx_get_tables(document_id: str) -> DocxGetTablesResult:
        request = SemanticDocumentRequest.model_validate({"document_id": document_id})
        return _run_tool(
            lambda: mcp_converters.convert_docx_get_tables(
                services.docx_get_tables(request.document_id)
            )
        )

    _register_v2_tools(mcp, services)
    _register_escape_hatch_tools(mcp, services)

    return mcp


def _register_v2_tools(mcp, services: AppServices) -> None:
    @mcp.tool(description="Return a structured V2 object payload for a typed locator.")
    def get_object(document_id: str, locator: str) -> GetObjectResult:
        request = GetObjectRequest.model_validate({"document_id": document_id, "locator": locator})
        return _run_tool(
            lambda: mcp_converters.convert_get_object(
                services.get_object(request.document_id, request.locator)
            )
        )

    @mcp.tool(description="List child objects for a V2 typed locator.")
    def list_children(
        document_id: str,
        locator: str,
        child_type: str | None = None,
        limit: int | None = None,
    ) -> ListChildrenResult:
        request = ListChildrenRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "child_type": child_type,
                "limit": limit,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_list_children(
                services.list_children(
                    request.document_id,
                    request.locator,
                    child_type=request.child_type,
                    limit=request.limit,
                )
            )
        )

    @mcp.tool(description="Create a new child object under a V2 parent locator.")
    def create_object(
        document_id: str,
        parent_locator: str,
        object_type: str,
        properties: dict,
        segments: list[dict] | None = None,
        range: dict | None = None,
        position: object | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = CreateObjectRequest.model_validate(
            {
                "document_id": document_id,
                "parent_locator": parent_locator,
                "object_type": object_type,
                "properties": properties,
                "segments": segments,
                "range": range,
                "position": position,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.create_object(
                    request.document_id,
                    request.parent_locator,
                    request.object_type,
                    request.properties,
                    request.position,
                    None if request.segments is None else [fragment.to_domain() for fragment in request.segments],
                    None if request.range is None else request.range.to_domain(),
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Update a V2 object using editable properties.")
    def update_object(
        document_id: str,
        locator: str,
        properties: dict,
        segments: list[dict] | None = None,
        range: dict | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = UpdateObjectRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "properties": properties,
                "segments": segments,
                "range": range,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.update_object(
                    request.document_id,
                    request.locator,
                    request.properties,
                    None if request.segments is None else [fragment.to_domain() for fragment in request.segments],
                    None if request.range is None else request.range.to_domain(),
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Move a V2 object within a valid parent container.")
    def move_object(
        document_id: str,
        locator: str,
        new_parent_locator: str,
        position: object | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = MoveObjectRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "new_parent_locator": new_parent_locator,
                "position": position,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.move_object(
                    request.document_id,
                    request.locator,
                    request.new_parent_locator,
                    request.position,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Copy a V2 object into a valid parent container.")
    def copy_object(
        document_id: str,
        locator: str,
        target_parent_locator: str,
        position: object | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = CopyObjectRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "target_parent_locator": target_parent_locator,
                "position": position,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.copy_object(
                    request.document_id,
                    request.locator,
                    request.target_parent_locator,
                    request.position,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Apply a sequence of V2 object operations atomically to a single document.")
    def batch_edit(
        document_id: str,
        operations: list[dict],
        output_mode: str = "versioned",
        dry_run: bool = False,
    ) -> BatchResultModel:
        request = BatchEditRequest.model_validate(
            {
                "document_id": document_id,
                "operations": operations,
                "output_mode": output_mode,
                "dry_run": dry_run,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_batch_result(
                services.batch_edit(
                    request.document_id,
                    request.operations,
                    output_mode=request.output_mode,
                    dry_run=request.dry_run,
                )
            )
        )

    @mcp.tool(description="Delete a V2 object when the locator advertises delete capability.")
    def delete_object(
        document_id: str,
        locator: str,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = DeleteObjectRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.delete_object(
                    request.document_id,
                    request.locator,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Search indexed Office document content and return V2 object locators.")
    def search_objects(
        query: str,
        file_type: str | None = None,
        document_id: str | None = None,
        mode: str = "keyword",
        limit: int = 20,
    ) -> SearchObjectsResult:
        request = SearchDocumentsRequest.model_validate(
            {
                "query": query,
                "file_type": file_type,
                "document_id": document_id,
                "mode": mode,
                "limit": limit,
            }
        )

        def runner() -> SearchObjectsResult:
            document_path = None
            if request.document_id is not None:
                document_path = services.resolve_document_path(request.document_id)
            hits = services.search_corpus(
                request.query,
                file_type=request.file_type,
                document_path=document_path,
                limit=request.limit,
                mode=request.mode,
            )
            return SearchObjectsResult.from_hits(hits)

        return _run_tool(runner)


def _register_escape_hatch_tools(mcp, services: AppServices) -> None:
    @mcp.tool(description="Apply a named DOCX paragraph style after validating the document style catalog.")
    def docx_set_paragraph_style(
        document_id: str,
        locator: str,
        style_name: str,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = DocxSetParagraphStyleRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "style_name": style_name,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.docx_set_paragraph_style(
                    request.document_id,
                    request.locator,
                    request.style_name,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Insert a DOCX page break after the referenced paragraph.")
    def docx_insert_page_break(
        document_id: str,
        locator: str,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = DocxInsertPageBreakRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.docx_insert_page_break(
                    request.document_id,
                    request.locator,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Insert a DOCX table with optional widths, style, and after-position.")
    def docx_add_table(
        document_id: str,
        row_count: int,
        column_count: int,
        position: object | None = None,
        column_widths: list[int] | None = None,
        style_name: str | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = DocxAddTableRequest.model_validate(
            {
                "document_id": document_id,
                "row_count": row_count,
                "column_count": column_count,
                "position": position,
                "column_widths": column_widths,
                "style_name": style_name,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.docx_add_table(
                    request.document_id,
                    request.row_count,
                    request.column_count,
                    position=request.position,
                    column_widths=request.column_widths,
                    style_name=request.style_name,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Merge a rectangular range of DOCX table cells.")
    def docx_merge_table_cells(
        document_id: str,
        start_locator: str,
        end_locator: str,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = DocxMergeTableCellsRequest.model_validate(
            {
                "document_id": document_id,
                "start_locator": start_locator,
                "end_locator": end_locator,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.docx_merge_table_cells(
                    request.document_id,
                    request.start_locator,
                    request.end_locator,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Add a new PPTX slide using a validated layout index or layout name.")
    def pptx_add_slide(
        document_id: str,
        layout_index: int | None = None,
        layout_name: str | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = PptxAddSlideRequest.model_validate(
            {
                "document_id": document_id,
                "layout_index": layout_index,
                "layout_name": layout_name,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.pptx_add_slide(
                    request.document_id,
                    layout_index=request.layout_index,
                    layout_name=request.layout_name,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Duplicate a PPTX slide into a target slide position.")
    def pptx_duplicate_slide(
        document_id: str,
        locator: str,
        position: int | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = PptxDuplicateSlideRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "position": position,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.pptx_duplicate_slide(
                    request.document_id,
                    request.locator,
                    position=request.position,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Reassign a PPTX slide to a validated layout.")
    def pptx_set_slide_layout(
        document_id: str,
        locator: str,
        layout_index: int | None = None,
        layout_name: str | None = None,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = PptxSetSlideLayoutRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "layout_index": layout_index,
                "layout_name": layout_name,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.pptx_set_slide_layout(
                    request.document_id,
                    request.locator,
                    layout_index=request.layout_index,
                    layout_name=request.layout_name,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Add a text box shape to a PPTX slide at the provided position and size.")
    def pptx_add_text_shape(
        document_id: str,
        locator: str,
        text: str,
        left: int,
        top: int,
        width: int,
        height: int,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = PptxAddTextShapeRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "text": text,
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.pptx_add_text_shape(
                    request.document_id,
                    request.locator,
                    request.text,
                    left=request.left,
                    top=request.top,
                    width=request.width,
                    height=request.height,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Write a 2D value grid into an XLSX range locator.")
    def xlsx_write_range(
        document_id: str,
        locator: str,
        values: list[list[object]],
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = XlsxWriteRangeRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "values": values,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.xlsx_write_range(
                    request.document_id,
                    request.locator,
                    request.values,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(
        description=(
            "Append rows to an XLSX worksheet using `sheet_name` plus `rows` or `records`, "
            "or insert blank rows using `locator`, `row_number`, and `count`."
        )
    )
    def xlsx_insert_rows(
        document_id: str,
        sheet_name: str | None = None,
        rows: list[list[str]] | None = None,
        records: list[dict[str, str]] | None = None,
        locator: str | None = None,
        row_number: int | None = None,
        count: int | None = None,
        output_mode: str = "versioned",
    ) -> XlsxInsertRowsResultModel:
        request = XlsxInsertRowsRequest.model_validate(
            {
                "document_id": document_id,
                "sheet_name": sheet_name,
                "rows": rows,
                "records": records,
                "locator": locator,
                "row_number": row_number,
                "count": count,
                "output_mode": output_mode,
            }
        )

        def runner() -> XlsxInsertRowsResultModel:
            if request.locator is not None or request.row_number is not None or request.count is not None:
                if request.locator is None or request.row_number is None or request.count is None:
                    raise InvalidArgumentsError(
                        "xlsx_insert_rows requires locator, row_number, and count for row insertion mode."
                    )
                result = services.xlsx_insert_rows_at(
                    request.document_id,
                    request.locator,
                    request.row_number,
                    request.count,
                    output_mode=request.output_mode,
                )
                return mcp_converters.convert_xlsx_insert_rows_result(result)

            if request.sheet_name is None:
                raise InvalidArgumentsError(
                    "xlsx_insert_rows requires sheet_name when using append rows mode."
                )
            result = services.xlsx_insert_rows(
                request.document_id,
                request.sheet_name,
                rows=request.rows,
                records=request.records,
                output_mode=request.output_mode,
            )
            return mcp_converters.convert_xlsx_insert_rows_result(result)

        return _run_tool(runner)

    @mcp.tool(description="Insert one or more blank columns into an XLSX worksheet.")
    def xlsx_insert_columns(
        document_id: str,
        locator: str,
        column_index: int,
        count: int,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = XlsxInsertColumnsRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "column_index": column_index,
                "count": count,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.xlsx_insert_columns(
                    request.document_id,
                    request.locator,
                    request.column_index,
                    request.count,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Write a validated formula string into an XLSX cell.")
    def xlsx_set_formula(
        document_id: str,
        locator: str,
        formula: str,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = XlsxSetFormulaRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "formula": formula,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.xlsx_set_formula(
                    request.document_id,
                    request.locator,
                    request.formula,
                    output_mode=request.output_mode,
                )
            )
        )

    @mcp.tool(description="Merge an XLSX rectangular range after overlap validation.")
    def xlsx_merge_cells(
        document_id: str,
        locator: str,
        output_mode: str = "versioned",
    ) -> MutationResultModel:
        request = XlsxMergeCellsRequest.model_validate(
            {
                "document_id": document_id,
                "locator": locator,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_mutation_result(
                services.xlsx_merge_cells(
                    request.document_id,
                    request.locator,
                    output_mode=request.output_mode,
                )
            )
        )


def run_mcp_server(config: AppConfig) -> None:
    build_mcp_server(config).run(transport="stdio")


def _run_tool(callback: Callable[[], T]) -> T:
    try:
        return callback()
    except EXPECTED_TOOL_ERRORS as exc:
        if ToolError is None:  # pragma: no cover - guarded by build_mcp_server
            raise RuntimeError(str(exc)) from exc
        raise ToolError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - exercised through integration tests
        LOGGER.exception("Unhandled MCP tool failure")
        if ToolError is None:
            raise RuntimeError("Internal Office Agent MCP tool failure.") from exc
        raise ToolError("Internal Office Agent MCP tool failure.") from exc
