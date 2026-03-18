from __future__ import annotations

from offagent.app.services import discover_documents


def test_discovers_only_supported_office_files(tmp_path) -> None:
    root = tmp_path
    (root / "proposal.docx").write_text("word")
    (root / "deck.pptx").write_text("slides")
    (root / "budget.xlsx").write_text("sheet")
    (root / "notes.txt").write_text("ignore")
    nested = root / "nested"
    nested.mkdir()
    (nested / "appendix.docx").write_text("nested")

    documents = discover_documents([root])

    assert [document.path.name for document in documents] == [
        "budget.xlsx",
        "deck.pptx",
        "appendix.docx",
        "proposal.docx",
    ]
    assert all(document.modified_time > 0 for document in documents)
    assert {document.file_type for document in documents} == {"docx", "pptx", "xlsx"}
