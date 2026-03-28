from __future__ import annotations

from offagent.domain.models import (
    DocxTablesResult,
    InsertContentResult,
    NodePayload,
    NodeWriteResult,
    SectionPayload,
    StructureCollection,
    XlsxInsertRowsResult,
)
from offagent.interfaces.mcp_models import (
    DocxGetTablesResult,
    GetNodeResult,
    GetSectionResult,
    GetStructureResult,
    InsertContentResultModel,
    WriteNodeResult,
    XlsxInsertRowsResultModel,
)


def convert_get_structure(result: StructureCollection) -> GetStructureResult:
    return GetStructureResult.from_domain(result)


def convert_get_section(result: SectionPayload) -> GetSectionResult:
    return GetSectionResult.from_domain(result)


def convert_get_node(result: NodePayload) -> GetNodeResult:
    return GetNodeResult.from_domain(result)


def convert_write_node(result: NodeWriteResult) -> WriteNodeResult:
    return WriteNodeResult.from_domain(result)


def convert_insert_content(result: InsertContentResult) -> InsertContentResultModel:
    return InsertContentResultModel.from_domain(result)


def convert_xlsx_insert_rows(result: XlsxInsertRowsResult) -> XlsxInsertRowsResultModel:
    return XlsxInsertRowsResultModel.from_domain(result)


def convert_docx_get_tables(result: DocxTablesResult) -> DocxGetTablesResult:
    return DocxGetTablesResult.from_domain(result)
