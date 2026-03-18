from __future__ import annotations

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


def test_extract_document_skips_empty_cells(sample_xlsx) -> None:
    items = xlsx_adapter.extract_document(sample_xlsx)

    assert "sheet:Notes 2026!B5" not in {item.item_id for item in items}
