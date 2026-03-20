from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from offagent.domain.models import IndexedItem
from offagent.errors import InvalidArgumentsError, TargetNotFoundError

try:
    from docx import Document
    from docx.shared import RGBColor
    from docx.text.run import Run
except ModuleNotFoundError:  # pragma: no cover - exercised through dependency checks
    Document = None
    RGBColor = None
    Run = None


@dataclass(frozen=True)
class RunFormatting:
    bold: bool | None
    italic: bool | None
    underline: bool | None
    strike: bool | None
    font_name: str | None
    font_size: int | None
    color_rgb: str | None


def extract_document(document_path: Path) -> list[IndexedItem]:
    document = _open_document(document_path)
    items: list[IndexedItem] = []

    for paragraph_index, paragraph in enumerate(document.paragraphs):
        style_name = paragraph.style.name if paragraph.style is not None else None
        is_heading = bool(style_name and style_name.startswith("Heading"))
        text = paragraph.text
        locator = f"para:{paragraph_index}"
        items.append(
            IndexedItem(
                item_id=locator,
                item_type="paragraph",
                locator=locator,
                preview=text[:120],
                content_text=text,
                metadata={
                    "paragraph_index": paragraph_index,
                    "style_name": style_name,
                    "is_heading": is_heading,
                },
            )
        )

    return items


def build_embedding_text(item: IndexedItem, document_path: Path) -> str:
    del document_path
    return item.content_text


def read_paragraph(document_path: Path, item_id: str) -> str:
    paragraph = _resolve_paragraph(_open_document(document_path), item_id)
    return paragraph.text


def replace_paragraph(document_path: Path, item_id: str, text: str, output_path: Path | None = None) -> Path:
    document = _open_document(document_path)
    paragraph = _resolve_paragraph(document, item_id)
    formatting = _capture_run_formatting(paragraph.runs[0] if paragraph.runs else None)
    _clear_paragraph(paragraph)
    replacement_run = paragraph.add_run(text)
    _apply_run_formatting(replacement_run, formatting)
    target_path = _target_path(document_path, output_path)
    document.save(target_path)
    return target_path


def append_paragraph(document_path: Path, item_id: str, text: str, output_path: Path | None = None) -> Path:
    document = _open_document(document_path)
    paragraph = _resolve_paragraph(document, item_id)
    if paragraph.runs:
        paragraph.runs[-1].text = f"{paragraph.runs[-1].text}{text}"
    else:
        paragraph.add_run(text)
    target_path = _target_path(document_path, output_path)
    document.save(target_path)
    return target_path


def _open_document(document_path: Path):
    if Document is None:
        raise RuntimeError("python-docx is required for DOCX operations.")
    return Document(str(document_path))


def _resolve_paragraph(document, item_id: str):
    if not item_id.startswith("para:"):
        raise InvalidArgumentsError(f"Unsupported DOCX paragraph item id: {item_id}")

    try:
        paragraph_index = int(item_id.split(":", maxsplit=1)[1])
    except ValueError as exc:
        raise InvalidArgumentsError(f"Invalid DOCX paragraph item id: {item_id}") from exc

    try:
        return document.paragraphs[paragraph_index]
    except IndexError as exc:
        raise TargetNotFoundError(
            f"Paragraph {paragraph_index} does not exist in the document."
        ) from exc


def _capture_run_formatting(run: Run | None) -> RunFormatting | None:
    if run is None:
        return None

    color_rgb = None
    if run.font.color.rgb is not None:
        color_rgb = str(run.font.color.rgb)

    font_size = None
    if run.font.size is not None:
        font_size = int(run.font.size)

    return RunFormatting(
        bold=run.bold,
        italic=run.italic,
        underline=run.underline,
        strike=run.font.strike,
        font_name=run.font.name,
        font_size=font_size,
        color_rgb=color_rgb,
    )


def _apply_run_formatting(run: Run, formatting: RunFormatting | None) -> None:
    if formatting is None:
        return

    run.bold = formatting.bold
    run.italic = formatting.italic
    run.underline = formatting.underline
    run.font.strike = formatting.strike
    run.font.name = formatting.font_name
    if formatting.font_size is not None:
        run.font.size = formatting.font_size
    if formatting.color_rgb is not None:
        run.font.color.rgb = RGBColor.from_string(formatting.color_rgb)


def _clear_paragraph(paragraph) -> None:
    paragraph_element = paragraph._element
    for child in list(paragraph_element):
        if child.tag.endswith("}pPr"):
            continue
        paragraph_element.remove(child)


def _target_path(document_path: Path, output_path: Path | None) -> Path:
    return document_path if output_path is None else output_path
