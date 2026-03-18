from __future__ import annotations

from docx import Document

from offagent.app.services import AppServices
from offagent.config import AppConfig


def test_index_search_locate_and_read_docx(sample_docx, tmp_path) -> None:
    services = AppServices(
        AppConfig(index_path=tmp_path / "state" / "index.sqlite3", document_roots=(tmp_path,))
    )

    summary = services.index_path(sample_docx)
    hits = services.search_corpus("Supplier shall", file_type="docx")
    item = services.locate_paragraph(sample_docx, 3)
    text = services.read_item(sample_docx, "para:3")

    assert summary.files_indexed == 1
    assert hits[0].item_id == "para:3"
    assert hits[0].preview == "Supplier shall deliver by Friday."
    assert item.item_id == "para:3"
    assert text == "Supplier shall deliver by Friday."


def test_replace_append_and_reindex_docx(sample_docx, tmp_path) -> None:
    services = AppServices(
        AppConfig(index_path=tmp_path / "state" / "index.sqlite3", document_roots=(tmp_path,))
    )
    services.index_document(sample_docx)

    replace_result = services.replace_item_text(sample_docx, "para:1", "Replaced alpha text.")
    append_result = services.append_item_text(sample_docx, "para:2", "Now populated.")

    document = Document(str(sample_docx))
    assert replace_result.text == "Replaced alpha text."
    assert append_result.text == "Now populated."
    assert document.paragraphs[1].runs[0].bold is True
    assert document.paragraphs[2].text == "Now populated."

    services.reindex_path(sample_docx)
    hits = services.search_corpus("Replaced alpha")
    assert hits[0].item_id == "para:1"
