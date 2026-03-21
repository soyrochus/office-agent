from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from offagent.domain.models import DocumentRef, IndexedItem
from offagent.indexing import store


def test_ensure_ready_creates_expected_schema(tmp_path) -> None:
    index_path = tmp_path / "index.sqlite3"
    connection = store.ensure_ready(index_path)
    try:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
    finally:
        connection.close()

    assert "documents" in table_names
    assert "items" in table_names
    assert "items_fts" in table_names
    assert "item_embeddings" in table_names
    assert "embedding_meta" in table_names
    assert "xlsx_row_embeddings" in table_names
    assert "xlsx_row_embedding_cells" in table_names


def test_initialize_schema_raises_without_fts5_support(monkeypatch) -> None:
    connection = sqlite3.connect(":memory:")
    try:
        monkeypatch.setattr("offagent.indexing.store.supports_fts5", lambda _: False)
        with pytest.raises(store.StoreCapabilityError):
            store.initialize_schema(connection)
    finally:
        connection.close()


def test_replace_xlsx_row_embeddings_replaces_previous_rows(tmp_path) -> None:
    connection = store.ensure_ready(tmp_path / "index.sqlite3")
    document = DocumentRef(
        document_id="doc-1",
        path=Path(tmp_path / "sample.xlsx"),
        file_type="xlsx",
        display_name="sample.xlsx",
        modified_time=1.0,
    )
    items = [
        IndexedItem(
            item_id="sheet:Sheet1!A1",
            item_type="cell",
            locator="sheet:Sheet1!A1",
            preview="Status",
            content_text="Status",
            metadata={"sheet_name": "Sheet1", "coordinate": "A1", "display_text": "Status"},
        ),
        IndexedItem(
            item_id="sheet:Sheet1!C1",
            item_type="cell",
            locator="sheet:Sheet1!C1",
            preview="Needs review",
            content_text="Needs review",
            metadata={"sheet_name": "Sheet1", "coordinate": "C1", "display_text": "Needs review"},
        ),
        IndexedItem(
            item_id="sheet:Sheet1!A2",
            item_type="cell",
            locator="sheet:Sheet1!A2",
            preview="Approved",
            content_text="Approved",
            metadata={"sheet_name": "Sheet1", "coordinate": "A2", "display_text": "Approved"},
        ),
    ]
    try:
        store.upsert_document(connection, document)
        store.replace_document_items(connection, document.document_id, items)
        store.replace_xlsx_row_embeddings(
            connection,
            document_id=document.document_id,
            model_name="hash://test",
            dimensions=8,
            row_embeddings=[
                (
                    store.make_xlsx_row_embedding_id(document.document_id, "Sheet1", 1),
                    "Sheet1",
                    1,
                    store.make_storage_id(document.document_id, "sheet:Sheet1!C1"),
                    "Workbook: sample.xlsx\nSheet: Sheet1\nRow: 1\nCells:\n- A1: Status\n- C1: Needs review",
                    "Needs review",
                    b"\x00" * 32,
                    [
                        (store.make_storage_id(document.document_id, "sheet:Sheet1!A1"), "A1", 1, False),
                        (store.make_storage_id(document.document_id, "sheet:Sheet1!C1"), "C1", 2, True),
                    ],
                )
            ],
        )
        store.replace_xlsx_row_embeddings(
            connection,
            document_id=document.document_id,
            model_name="hash://test",
            dimensions=8,
            row_embeddings=[
                (
                    store.make_xlsx_row_embedding_id(document.document_id, "Sheet1", 2),
                    "Sheet1",
                    2,
                    store.make_storage_id(document.document_id, "sheet:Sheet1!A2"),
                    "Workbook: sample.xlsx\nSheet: Sheet1\nRow: 2\nCells:\n- A2: Approved",
                    "Approved",
                    b"\x01" * 32,
                    [
                        (store.make_storage_id(document.document_id, "sheet:Sheet1!A2"), "A2", 1, True),
                    ],
                )
            ],
        )
        connection.commit()

        rows = store.fetch_xlsx_row_embeddings(connection, file_type="xlsx")
        cells = store.fetch_xlsx_row_embedding_cells(
            connection,
            store.make_xlsx_row_embedding_id(document.document_id, "Sheet1", 2),
        )
    finally:
        connection.close()

    assert [(row["sheet_name"], row["row_number"], row["item_id"]) for row in rows] == [
        ("Sheet1", 2, "sheet:Sheet1!A2")
    ]
    assert [cell["cell_coordinate"] for cell in cells] == ["A2"]
