from __future__ import annotations

from openpyxl import Workbook

from offagent.adapters import xlsx_adapter


def test_extract_document_captures_cells_and_metadata(sample_xlsx) -> None:
    items = xlsx_adapter.extract_document(sample_xlsx)

    assert [item.item_id for item in items] == [
        "sheet:Budget2026!A1",
        "sheet:Budget2026!B2",
        "sheet:Budget2026!C3",
        "sheet:Notes 2026!A1",
        "sheet:Notes 2026!A2",
    ]
    assert all(item.item_type == "cell" for item in items)

    formula_item = next(item for item in items if item.item_id == "sheet:Budget2026!C3")
    assert formula_item.content_text == "=SUM(1,2)"
    assert formula_item.metadata["sheet_name"] == "Budget2026"
    assert formula_item.metadata["coordinate"] == "C3"
    assert formula_item.metadata["formula"] == "=SUM(1,2)"
    assert "row_context" in formula_item.metadata
    assert "column_context" in formula_item.metadata


def test_extract_document_skips_empty_cells(sample_xlsx) -> None:
    items = xlsx_adapter.extract_document(sample_xlsx)

    assert "sheet:Notes 2026!B5" not in {item.item_id for item in items}


def test_build_embedding_text_uses_contextual_metadata(sample_xlsx) -> None:
    items = xlsx_adapter.extract_document(sample_xlsx)
    note_item = next(item for item in items if item.item_id == "sheet:Notes 2026!A1")

    text = xlsx_adapter.build_embedding_text(note_item, sample_xlsx)

    assert "Workbook: sample.xlsx" in text
    assert "Sheet: Notes 2026" in text
    assert "Cell: A1" in text
    assert "Column Context: Follow up with finance." in text
    assert "Value: Supplier shall review variance." in text


def test_build_row_embeddings_filters_numeric_and_formula_cells(sample_xlsx) -> None:
    items = xlsx_adapter.extract_document(sample_xlsx)

    row_embeddings = xlsx_adapter.build_row_embeddings(items, sample_xlsx)

    assert [
        (row.sheet_name, row.row_number, row.representative_item_id)
        for row in row_embeddings
    ] == [
        ("Budget2026", 1, "sheet:Budget2026!A1"),
        ("Notes 2026", 1, "sheet:Notes 2026!A1"),
        ("Notes 2026", 2, "sheet:Notes 2026!A2"),
    ]
    assert all(
        [cell.coordinate for cell in row.contributing_cells] in (["A1"], ["A2"])
        for row in row_embeddings
    )


def test_build_row_embeddings_preserve_mixed_text_rows_and_pick_representative(tmp_path) -> None:
    path = tmp_path / "mixed.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sheet1"
    worksheet["A1"] = "Status"
    worksheet["B1"] = 125000
    worksheet["C1"] = "Needs review"
    workbook.save(path)

    items = xlsx_adapter.extract_document(path)
    row_embeddings = xlsx_adapter.build_row_embeddings(items, path)

    assert len(row_embeddings) == 1
    row_embedding = row_embeddings[0]
    assert row_embedding.representative_item_id == "sheet:Sheet1!C1"
    assert [cell.coordinate for cell in row_embedding.contributing_cells] == ["A1", "C1"]
    assert "A1: Status" in row_embedding.text
    assert "C1: Needs review" in row_embedding.text
    assert "B1: 125000" not in row_embedding.text
