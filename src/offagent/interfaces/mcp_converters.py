from __future__ import annotations

from offagent.domain.models import (
    BatchResult,
    ChildSummary,
    DocxTablesResult,
    InsertContentResult,
    MutationResult,
    NodePayload,
    NodeWriteResult,
    ObjectPayload,
    SectionPayload,
    StructureCollection,
    XlsxInsertRowsResult,
)
from offagent.interfaces.mcp_models import (
    BatchResultModel,
    DocxGetTablesResult,
    GetNodeResult,
    GetObjectResult,
    GetSectionResult,
    GetStructureResult,
    InsertContentResultModel,
    ListChildrenResult,
    MutationResultModel,
    WriteNodeResult,
    XlsxInsertRowsResultModel,
)


def convert_get_structure(result: StructureCollection) -> GetStructureResult:
    return GetStructureResult.from_domain(result)


def convert_get_section(result: SectionPayload) -> GetSectionResult:
    return GetSectionResult.from_domain(result)


def convert_get_node(result: NodePayload) -> GetNodeResult:
    return GetNodeResult.from_domain(result)


def convert_get_object(result: ObjectPayload) -> GetObjectResult:
    return GetObjectResult.from_domain(result)


def convert_list_children(result: list[ChildSummary]) -> ListChildrenResult:
    return ListChildrenResult.from_domain(result)


def convert_write_node(result: NodeWriteResult) -> WriteNodeResult:
    return WriteNodeResult.from_domain(result)


def convert_insert_content(result: InsertContentResult) -> InsertContentResultModel:
    return InsertContentResultModel.from_domain(result)


def convert_mutation_result(result: MutationResult) -> MutationResultModel:
    return MutationResultModel.from_domain(result)


def convert_batch_result(result: BatchResult) -> BatchResultModel:
    return BatchResultModel.from_domain(result)


def convert_xlsx_insert_rows(result: XlsxInsertRowsResult) -> XlsxInsertRowsResultModel:
    return XlsxInsertRowsResultModel.from_domain(result)


def convert_xlsx_insert_rows_result(
    result: XlsxInsertRowsResult | MutationResult,
) -> XlsxInsertRowsResultModel:
    if isinstance(result, MutationResult):
        return XlsxInsertRowsResultModel.from_mutation_result(result)
    return XlsxInsertRowsResultModel.from_domain(result)


def convert_docx_get_tables(result: DocxTablesResult) -> DocxGetTablesResult:
    return DocxGetTablesResult.from_domain(result)
