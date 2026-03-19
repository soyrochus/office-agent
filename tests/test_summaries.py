from __future__ import annotations

from offagent.app.services import AppServices
from offagent.config import AppConfig


def test_list_documents_and_show_item_include_summary_details(sample_docx, tmp_path) -> None:
    services = AppServices(
        AppConfig(index_path=tmp_path / "state" / "index.sqlite3", document_roots=(tmp_path,))
    )
    services.index_document(sample_docx)

    documents = services.list_documents()
    document = services.show_document(sample_docx)
    item = services.show_item(sample_docx, "para:3")

    assert len(documents) == 1
    assert documents[0].item_count == 4
    assert document.item_count == 4
    assert item.item_id == "para:3"
    assert item.content_text == "Supplier shall deliver by Friday."
