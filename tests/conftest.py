from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from pptx.util import Inches


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


@pytest.fixture
def sample_pptx(tmp_path) -> Path:
    path = tmp_path / "sample.pptx"
    presentation = Presentation()

    first_slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    title = first_slide.shapes.title
    title.text = "Quarterly Planning"

    summary_box = first_slide.shapes.add_textbox(Inches(1), Inches(1.8), Inches(5), Inches(1.5))
    summary_frame = summary_box.text_frame
    summary_frame.text = "Alpha launch overview"
    summary_frame.add_paragraph().text = "Supplier shall present the rollout plan."

    notes_box = first_slide.shapes.add_textbox(Inches(1), Inches(3.7), Inches(4.5), Inches(1))
    notes_box.text = "Secondary text frame"

    table_shape = first_slide.shapes.add_table(2, 2, Inches(6), Inches(1.8), Inches(3), Inches(1.5))
    table_shape.table.cell(0, 0).text = "Table text to ignore"

    second_slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    editable_box = second_slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(5.5), Inches(1.5))
    editable_box.text = "Editable speaker notes"

    presentation.save(path)
    return path


@pytest.fixture
def sample_xlsx(tmp_path) -> Path:
    path = tmp_path / "sample.xlsx"
    workbook = Workbook()

    budget_sheet = workbook.active
    budget_sheet.title = "Budget2026"
    budget_sheet["A1"] = "Quarterly Budget"
    budget_sheet["B2"] = 125000
    budget_sheet["C3"] = "=SUM(1,2)"

    notes_sheet = workbook.create_sheet("Notes 2026")
    notes_sheet["A1"] = "Supplier shall review variance."
    notes_sheet["A2"] = "Follow up with finance."

    workbook.save(path)
    return path
