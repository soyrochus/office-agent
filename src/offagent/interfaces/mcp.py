from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, TypeVar

from offagent.adapters import pptx_adapter, xlsx_adapter
from offagent.app.services import AppServices
from offagent.config import AppConfig
from offagent.domain.locators import parse_locator
from offagent.domain.models import DocumentRef, ItemRef
from offagent.errors import (
    InvalidArgumentsError,
    PolicyRefusedError,
    StaleLocatorError,
    TargetNotEditableError,
    TargetNotFoundError,
)
from offagent.interfaces.mcp_models import (
    AppendTextRequest,
    IndexDocumentsRequest,
    IndexDocumentsResult,
    IndexPathResult,
    ListDocumentsResult,
    LocateItemRequest,
    LocateItemResult,
    ReadItemRequest,
    ReadItemResult,
    RefreshDocumentRequest,
    RefreshDocumentResult,
    ReplaceTextRequest,
    SearchDocumentsRequest,
    SearchDocumentsResult,
    WriteCellRequest,
    WriteResult,
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
    "Office Agent exposes indexed Office document workflows as MCP tools. "
    "Use the tools for indexing, search, locate, read, and supported write operations "
    "against DOCX, PPTX, and XLSX documents."
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

    @mcp.tool(description="Resolve a document locator to a single indexed item.")
    def locate_item(document_id: str, locator: str) -> LocateItemResult:
        request = LocateItemRequest.model_validate({"document_id": document_id, "locator": locator})

        def runner() -> LocateItemResult:
            document = services.get_document(request.document_id)
            item = _locate_item(services, document, request.locator)
            return LocateItemResult.from_item(item)

        return _run_tool(runner)

    @mcp.tool(description="Read the current content for an indexed item.")
    def read_item(document_id: str, item_id: str) -> ReadItemResult:
        request = ReadItemRequest.model_validate({"document_id": document_id, "item_id": item_id})

        def runner() -> ReadItemResult:
            document_path = services.resolve_document_path(request.document_id)
            return ReadItemResult(
                document_id=request.document_id,
                item_id=request.item_id,
                text=services.read_item(document_path, request.item_id),
            )

        return _run_tool(runner)

    @mcp.tool(description="Replace indexed text content in a DOCX or PPTX item.")
    def replace_text(
        document_id: str,
        item_id: str,
        new_text: str,
        output_mode: str = "versioned",
    ) -> WriteResult:
        request = ReplaceTextRequest.model_validate(
            {
                "document_id": document_id,
                "item_id": item_id,
                "new_text": new_text,
                "output_mode": output_mode,
            }
        )

        def runner() -> WriteResult:
            document_path = services.resolve_document_path(request.document_id)
            result = services.replace_item_text(
                document_path,
                request.item_id,
                request.new_text,
                output_mode=request.output_mode,
            )
            return WriteResult.from_patch_result(result)

        return _run_tool(runner)

    @mcp.tool(description="Append text to an indexed item in a supported document type.")
    def append_text(
        document_id: str,
        item_id: str,
        text_to_add: str,
        output_mode: str = "versioned",
    ) -> WriteResult:
        request = AppendTextRequest.model_validate(
            {
                "document_id": document_id,
                "item_id": item_id,
                "text_to_add": text_to_add,
                "output_mode": output_mode,
            }
        )

        def runner() -> WriteResult:
            document_path = services.resolve_document_path(request.document_id)
            result = services.append_item_text(
                document_path,
                request.item_id,
                request.text_to_add,
                output_mode=request.output_mode,
            )
            return WriteResult.from_patch_result(result)

        return _run_tool(runner)

    @mcp.tool(description="Write a cell value in an indexed XLSX workbook.")
    def write_cell(
        document_id: str,
        sheet: str,
        cell: str,
        value: str,
        output_mode: str = "versioned",
    ) -> WriteResult:
        request = WriteCellRequest.model_validate(
            {
                "document_id": document_id,
                "sheet": sheet,
                "cell": cell,
                "value": value,
                "output_mode": output_mode,
            }
        )

        def runner() -> WriteResult:
            document_path = services.resolve_document_path(request.document_id)
            result = services.write_cell_value(
                document_path,
                request.sheet,
                request.cell,
                request.value,
                output_mode=request.output_mode,
            )
            return WriteResult.from_patch_result(result)

        return _run_tool(runner)

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


def _locate_item(services: AppServices, document: DocumentRef, locator: str) -> ItemRef:
    parsed = parse_locator(locator)

    if document.file_type == "docx":
        paragraph_index = _parse_docx_locator(parsed.raw)
        return services.locate_paragraph(document.path, paragraph_index)

    if document.file_type == "pptx":
        slide_number, shape_id = _parse_pptx_locator(parsed.raw)
        return services.locate_slide_shapes(document.path, slide_number, shape_id=shape_id)[0]

    sheet_name, cell_coordinate = _parse_xlsx_locator(parsed.raw)
    return services.locate_cell(document.path, sheet_name, cell_coordinate)


def _parse_docx_locator(locator: str) -> int:
    normalized = locator.strip()
    lowered = normalized.lower()
    if lowered.startswith("para:"):
        try:
            return int(normalized.split(":", maxsplit=1)[1])
        except ValueError as exc:
            raise InvalidArgumentsError(f"Invalid DOCX paragraph locator: {locator}") from exc
    if lowered.startswith("paragraph "):
        try:
            return int(normalized.split()[-1])
        except ValueError as exc:
            raise InvalidArgumentsError(f"Invalid DOCX paragraph locator: {locator}") from exc
    raise InvalidArgumentsError("DOCX locate_item expects a locator like `para:3` or `paragraph 3`.")


def _parse_pptx_locator(locator: str) -> tuple[int, int]:
    normalized = locator.strip()
    lowered = normalized.lower()
    if lowered.startswith("slide:") and ":shape:" in lowered:
        return pptx_adapter.parse_item_id(normalized)

    if lowered.startswith("slide "):
        tokens = normalized.split()
        if len(tokens) == 4 and tokens[2].lower() == "shape":
            try:
                return int(tokens[1]), int(tokens[3])
            except ValueError as exc:
                raise InvalidArgumentsError(f"Invalid PPTX locator: {locator}") from exc

    raise InvalidArgumentsError(
        "PPTX locate_item expects an exact shape locator like `slide:1:shape:3`."
    )


def _parse_xlsx_locator(locator: str) -> tuple[str, str]:
    normalized = locator.strip()
    lowered = normalized.lower()
    if lowered.startswith("sheet:") and "!" in normalized:
        return xlsx_adapter.parse_item_id(normalized)

    if lowered.startswith("sheet "):
        payload = normalized[6:].strip()
        if " " not in payload:
            raise InvalidArgumentsError(f"Invalid XLSX locator: {locator}")
        sheet_name, coordinate = payload.rsplit(" ", maxsplit=1)
        _, normalized_coordinate = xlsx_adapter.parse_item_id(f"sheet:{sheet_name}!{coordinate}")
        return sheet_name, normalized_coordinate

    raise InvalidArgumentsError("XLSX locate_item expects a locator like `sheet:Sheet1!A1`.")
