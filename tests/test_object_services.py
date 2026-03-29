from __future__ import annotations

from openpyxl import load_workbook

from offagent.app.services import AppServices, StaleLocatorError
from offagent.config import AppConfig


def test_get_object_and_list_children_dispatch_across_formats(sample_docx, sample_pptx, sample_xlsx, tmp_path) -> None:
    services = AppServices(
        AppConfig(index_path=tmp_path / "state" / "index.sqlite3", document_roots=(tmp_path,))
    )
    docx_document = services.index_document(sample_docx)
    pptx_document = services.index_document(sample_pptx)
    xlsx_document = services.index_document(sample_xlsx)

    docx_object = services.get_object(docx_document.document_id, "docx:para:1")
    pptx_object = services.get_object(pptx_document.document_id, "pptx:slide:1")
    xlsx_object = services.get_object(xlsx_document.document_id, "xlsx:sheet:Budget2026")

    docx_children = services.list_children(docx_document.document_id, "docx:document", child_type="paragraph")
    pptx_children = services.list_children(pptx_document.document_id, "pptx:slide:1", child_type="text_shape")
    xlsx_children = services.list_children(xlsx_document.document_id, "xlsx:sheet:Budget2026", child_type="row", limit=2)

    assert docx_object.object_type == "paragraph"
    assert pptx_object.object_type == "slide"
    assert xlsx_object.object_type == "worksheet"
    assert [child.locator for child in docx_children] == [
        "docx:para:0",
        "docx:para:1",
        "docx:para:2",
        "docx:para:3",
    ]
    assert pptx_children
    assert all(child.object_type == "text_shape" for child in pptx_children)
    assert [child.locator for child in xlsx_children] == [
        "xlsx:sheet:Budget2026:row:1",
        "xlsx:sheet:Budget2026:row:2",
    ]


def test_get_object_reports_stale_locator_after_external_change(sample_xlsx, tmp_path) -> None:
    services = AppServices(
        AppConfig(index_path=tmp_path / "state" / "index.sqlite3", document_roots=(tmp_path,))
    )
    document = services.index_document(sample_xlsx)

    workbook = load_workbook(sample_xlsx)
    del workbook["Budget2026"]
    workbook.save(sample_xlsx)

    try:
        services.get_object(document.document_id, "xlsx:sheet:Budget2026")
    except StaleLocatorError as exc:
        assert "stale locator" in str(exc)
    else:  # pragma: no cover - defensive guard for explicit failure messaging
        raise AssertionError("Expected stale locator error for deleted worksheet.")
