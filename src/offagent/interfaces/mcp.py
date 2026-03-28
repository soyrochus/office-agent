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
    DocxGetTablesResult,
    GetNodeResult,
    GetSectionResult,
    GetStructureResult,
    IndexDocumentsRequest,
    IndexDocumentsResult,
    IndexPathResult,
    InsertContentRequest,
    InsertContentResultModel,
    ListDocumentsResult,
    NodeRequest,
    RefreshDocumentRequest,
    RefreshDocumentResult,
    SearchDocumentsRequest,
    SearchDocumentsResult,
    SectionRequest,
    SemanticDocumentRequest,
    WriteNodeRequest,
    WriteNodeResult,
    XlsxInsertRowsRequest,
    XlsxInsertRowsResultModel,
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
    "Office Agent exposes 11 MCP tools for Office document workflows. "
    "Use `get_structure` to navigate a document, `get_section` to inspect one section, "
    "and `get_node` or `write_node` for leaf-node reads and writes. "
    "Any locator returned by search or structure tools is valid in `get_node` and `write_node` "
    "for the same document version. Format-specific tools are `insert_content`, "
    "`xlsx_insert_rows`, and `docx_get_tables`."
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

    @mcp.tool(description="Search indexed Office document content.")
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

    @mcp.tool(description="Append one or more rows to an indexed XLSX worksheet in a single write.")
    def xlsx_insert_rows(
        document_id: str,
        sheet_name: str,
        rows: list[list[str]] | None = None,
        records: list[dict[str, str]] | None = None,
        output_mode: str = "versioned",
    ) -> XlsxInsertRowsResultModel:
        request = XlsxInsertRowsRequest.model_validate(
            {
                "document_id": document_id,
                "sheet_name": sheet_name,
                "rows": rows,
                "records": records,
                "output_mode": output_mode,
            }
        )
        return _run_tool(
            lambda: mcp_converters.convert_xlsx_insert_rows(
                services.xlsx_insert_rows(
                    request.document_id,
                    request.sheet_name,
                    rows=request.rows,
                    records=request.records,
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

    return mcp


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
