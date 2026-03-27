from __future__ import annotations

import pytest
from docx import Document
from openpyxl import Workbook, load_workbook

from offagent.app.services import AppServices
from offagent.config import AppConfig
from offagent.errors import InvalidArgumentsError, TargetNotEditableError


def _services(tmp_path):
    edited_dir = tmp_path / "edited"
    return AppServices(
        AppConfig(
            index_path=tmp_path / "state" / "index.sqlite3",
            document_roots=(tmp_path,),
            output_directory=edited_dir,
            output_roots=(edited_dir, tmp_path),
        )
    )


def test_semantic_service_reads_across_formats(sample_docx, sample_pptx, sample_xlsx, tmp_path) -> None:
    services = _services(tmp_path)
    docx_document = services.index_document(sample_docx)
    pptx_document = services.index_document(sample_pptx)
    xlsx_document = services.index_document(sample_xlsx)

    docx_structure = services.get_document_structure(docx_document.document_id)
    pptx_structure = services.get_document_structure(pptx_document.document_id)
    xlsx_structure = services.get_document_structure(xlsx_document.document_id)
    slide_bundle = services.get_slide_bundle(pptx_document.document_id, 1)
    block_bundle = services.get_block_bundle(docx_document.document_id, 4)
    sheet_snapshot = services.get_sheet_snapshot(
        xlsx_document.document_id,
        "Notes 2026",
        start_cell="A1",
        row_count=2,
        column_count=2,
    )

    assert [unit.unit_type for unit in docx_structure.units] == [
        "paragraph",
        "paragraph",
        "paragraph",
        "paragraph",
        "table",
    ]
    assert [unit.unit_type for unit in pptx_structure.units] == ["slide", "slide"]
    assert [unit.metadata["sheet_name"] for unit in xlsx_structure.units] == ["Budget2026", "Notes 2026"]
    assert slide_bundle.notes_text == "Speaker notes: confirm launch owner."
    assert block_bundle.table is not None
    assert block_bundle.table.rows[0][0] == "Table text to ignore"
    assert [cell.coordinate for cell in sheet_snapshot.cells] == ["A1", "B1", "A2", "B2"]


def test_semantic_service_writes_return_structured_results_without_reindex(sample_docx, sample_xlsx, tmp_path) -> None:
    services = _services(tmp_path)
    docx_document = services.index_document(sample_docx)
    xlsx_document = services.index_document(sample_xlsx)

    append_result = services.append_paragraph(
        docx_document.document_id,
        "Semantic appendix paragraph.",
        style_name="Heading 2",
    )
    replace_result = services.replace_block(
        docx_document.document_id,
        1,
        "Semantic replacement paragraph.",
    )
    append_row_result = services.append_row(
        xlsx_document.document_id,
        "Notes 2026",
        values=["Escalate owner", "Finance"],
    )

    appended_document = Document(str(append_result.output_path))
    replaced_document = Document(str(replace_result.output_path))
    appended_workbook = load_workbook(append_row_result.output_path)

    assert append_result.target.identifier == "block:5"
    assert append_result.target.metadata["block_type"] == "paragraph"
    assert appended_document.paragraphs[-1].text == "Semantic appendix paragraph."
    assert appended_document.paragraphs[-1].style.name == "Heading 2"
    assert replaced_document.paragraphs[1].text == "Semantic replacement paragraph."
    assert append_row_result.target.identifier == "Notes 2026!row:3"
    assert appended_workbook["Notes 2026"]["A3"].value == "Escalate owner"
    assert services.search_corpus("Semantic appendix paragraph", file_type="docx") == []


def test_semantic_service_rejects_unsupported_targets(sample_docx, sample_xlsx, tmp_path) -> None:
    services = _services(tmp_path)
    docx_document = services.index_document(sample_docx)
    xlsx_document = services.index_document(sample_xlsx)

    with pytest.raises(TargetNotEditableError, match="table block replacement"):
        services.replace_block(docx_document.document_id, 4, "blocked")

    with pytest.raises(InvalidArgumentsError, match="requires a .xlsx document"):
        services.append_row(docx_document.document_id, "Sheet1", values=["blocked"])

    with pytest.raises(InvalidArgumentsError, match="requires a .docx document"):
        services.get_document_blocks(xlsx_document.document_id)


def test_semantic_service_write_table_supports_mapped_records(tmp_path) -> None:
    services = _services(tmp_path)
    workbook_path = tmp_path / "mapped.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Tasks"
    worksheet["A1"] = "Task"
    worksheet["B1"] = "Owner"
    workbook.save(workbook_path)
    document = services.index_document(workbook_path)

    result = services.write_table(
        document.document_id,
        "Tasks",
        records=[
            {"task": "Review budget", "owner": "Finance"},
            {"task": "Confirm launch", "owner": "Operations"},
        ],
        column_mapping={"task": "Task", "owner": "Owner"},
    )

    written_workbook = load_workbook(result.output_path)
    assert result.target.identifier == "Tasks!rows:2-3"
    assert written_workbook["Tasks"]["A2"].value == "Review budget"
    assert written_workbook["Tasks"]["B3"].value == "Operations"
