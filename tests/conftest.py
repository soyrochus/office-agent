from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document


@pytest.fixture
def sample_docx(tmp_path) -> Path:
    path = tmp_path / "sample.docx"
    document = Document()
    document.add_heading("Project Heading", level=1)
    paragraph = document.add_paragraph()
    first_run = paragraph.add_run("Alpha paragraph for search.")
    first_run.bold = True
    document.add_paragraph("")
    document.add_paragraph("Supplier shall deliver by Friday.")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Table text to ignore"
    document.save(path)
    return path


@pytest.fixture
def config_path(tmp_path) -> Path:
    path = tmp_path / "office-agent.toml"
    path.write_text(
        f"""
[offagent]
index_path = "{(tmp_path / 'state' / 'index.sqlite3').as_posix()}"
document_roots = ["{tmp_path.as_posix()}"]
""".strip()
    )
    return path
