from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from offagent.domain.models import (
    BlockBundle,
    DocxParagraph,
    DocxTable,
    DocumentBlock,
    DocumentRef,
    IndexedItem,
)
from offagent.errors import InvalidArgumentsError, TargetNotEditableError, TargetNotFoundError

try:
    from docx import Document
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.shared import RGBColor
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.text.run import Run
except ModuleNotFoundError:  # pragma: no cover - exercised through dependency checks
    Document = None
    CT_Tbl = None
    CT_P = None
    RGBColor = None
    Table = None
    Paragraph = None
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
    items: list[IndexedItem] = []

    for paragraph in get_paragraphs(document_path):
        locator = f"para:{paragraph.paragraph_index}"
        items.append(
            IndexedItem(
                item_id=locator,
                item_type="paragraph",
                locator=locator,
                preview=paragraph.preview,
                content_text=paragraph.text,
                metadata={
                    "paragraph_index": paragraph.paragraph_index,
                    "block_index": paragraph.block_index,
                    "style_name": paragraph.style_name,
                    "is_heading": paragraph.is_heading,
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


def get_blocks(document_path: Path) -> tuple[DocumentBlock, ...]:
    document = _open_document(document_path)
    blocks: list[DocumentBlock] = []

    paragraph_index = 0
    table_index = 0
    for block_index, (block_type, block) in enumerate(_iter_blocks(document)):
        if block_type == "paragraph":
            paragraph_model = _paragraph_model(block, block_index, paragraph_index)
            blocks.append(
                DocumentBlock(
                    block_index=block_index,
                    block_type="paragraph",
                    preview=paragraph_model.preview,
                    metadata={
                        "paragraph_index": paragraph_model.paragraph_index,
                        "style_name": paragraph_model.style_name,
                        "is_heading": paragraph_model.is_heading,
                    },
                )
            )
            paragraph_index += 1
        else:
            table_model = _table_model(block, block_index, table_index)
            blocks.append(
                DocumentBlock(
                    block_index=block_index,
                    block_type="table",
                    preview=table_model.preview,
                    metadata={
                        "table_index": table_model.table_index,
                        "row_count": len(table_model.rows),
                        "column_count": max((len(row) for row in table_model.rows), default=0),
                    },
                )
            )
            table_index += 1

    return tuple(blocks)


def get_paragraphs(document_path: Path) -> tuple[DocxParagraph, ...]:
    document = _open_document(document_path)
    paragraphs: list[DocxParagraph] = []

    paragraph_index = 0
    for block_index, (block_type, block) in enumerate(_iter_blocks(document)):
        if block_type != "paragraph":
            continue
        paragraphs.append(_paragraph_model(block, block_index, paragraph_index))
        paragraph_index += 1

    return tuple(paragraphs)


def get_tables(document_path: Path) -> tuple[DocxTable, ...]:
    document = _open_document(document_path)
    tables: list[DocxTable] = []

    table_index = 0
    for block_index, (block_type, block) in enumerate(_iter_blocks(document)):
        if block_type != "table":
            continue
        tables.append(_table_model(block, block_index, table_index))
        table_index += 1

    return tuple(tables)


def get_block_bundle(document_path: Path, block_index: int) -> BlockBundle:
    document = _open_document(document_path)

    paragraph_index = 0
    table_index = 0
    for current_block_index, (block_type, block) in enumerate(_iter_blocks(document)):
        if current_block_index != block_index:
            if block_type == "paragraph":
                paragraph_index += 1
            else:
                table_index += 1
            continue

        if block_type == "paragraph":
            paragraph_model = _paragraph_model(block, current_block_index, paragraph_index)
            return BlockBundle(
                document=_document_ref(document_path),
                block=DocumentBlock(
                    block_index=current_block_index,
                    block_type="paragraph",
                    preview=paragraph_model.preview,
                    metadata={
                        "paragraph_index": paragraph_model.paragraph_index,
                        "style_name": paragraph_model.style_name,
                        "is_heading": paragraph_model.is_heading,
                    },
                ),
                paragraph=paragraph_model,
            )

        table_model = _table_model(block, current_block_index, table_index)
        return BlockBundle(
            document=_document_ref(document_path),
            block=DocumentBlock(
                block_index=current_block_index,
                block_type="table",
                preview=table_model.preview,
                metadata={
                    "table_index": table_model.table_index,
                    "row_count": len(table_model.rows),
                    "column_count": max((len(row) for row in table_model.rows), default=0),
                },
            ),
            table=table_model,
        )

    raise TargetNotFoundError(f"Block {block_index} does not exist in the document.")


def append_paragraph_block(
    document_path: Path,
    text: str,
    *,
    style_name: str | None = None,
    output_path: Path | None = None,
) -> tuple[Path, int]:
    document = _open_document(document_path)
    block_index = len(list(_iter_blocks(document)))
    paragraph = document.add_paragraph(text)
    if style_name is not None:
        try:
            paragraph.style = style_name
        except (KeyError, ValueError) as exc:
            raise InvalidArgumentsError(f"Unknown DOCX paragraph style: {style_name}") from exc
    target_path = _target_path(document_path, output_path)
    document.save(target_path)
    return target_path, block_index


def replace_block(document_path: Path, block_index: int, text: str, output_path: Path | None = None) -> Path:
    document = _open_document(document_path)

    paragraph_index = 0
    for current_block_index, (block_type, block) in enumerate(_iter_blocks(document)):
        if current_block_index != block_index:
            if block_type == "paragraph":
                paragraph_index += 1
            continue

        if block_type == "table":
            raise TargetNotEditableError("DOCX table block replacement is not supported.")

        item_id = f"para:{paragraph_index}"
        return replace_paragraph(document_path, item_id, text, output_path)

    raise TargetNotFoundError(f"Block {block_index} does not exist in the document.")


def _open_document(document_path: Path):
    if Document is None:
        raise RuntimeError("python-docx is required for DOCX operations.")
    return Document(str(document_path))


def _document_ref(document_path: Path):
    resolved_path = document_path.resolve()
    stat = resolved_path.stat()
    return DocumentRef(
        document_id=resolved_path.as_posix(),
        path=resolved_path,
        file_type="docx",
        display_name=resolved_path.name,
        modified_time=stat.st_mtime,
    )


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


def _iter_blocks(document) -> list[tuple[str, Paragraph | Table]]:
    if CT_P is None or CT_Tbl is None or Paragraph is None or Table is None:
        raise RuntimeError("python-docx is required for DOCX operations.")

    parent = document.element.body
    blocks: list[tuple[str, Paragraph | Table]] = []
    for child in parent.iterchildren():
        if isinstance(child, CT_P):
            blocks.append(("paragraph", Paragraph(child, document)))
        elif isinstance(child, CT_Tbl):
            blocks.append(("table", Table(child, document)))
    return blocks


def _paragraph_model(paragraph, block_index: int, paragraph_index: int) -> DocxParagraph:
    style_name = paragraph.style.name if paragraph.style is not None else None
    is_heading = bool(style_name and style_name.startswith("Heading"))
    text = paragraph.text
    return DocxParagraph(
        block_index=block_index,
        paragraph_index=paragraph_index,
        text=text,
        style_name=style_name,
        is_heading=is_heading,
        preview=text[:120],
        metadata={},
    )


def _table_model(table, block_index: int, table_index: int) -> DocxTable:
    rows = tuple(tuple(cell.text for cell in row.cells) for row in table.rows)
    preview = " | ".join(cell for row in rows for cell in row if cell)[:120]
    return DocxTable(
        block_index=block_index,
        table_index=table_index,
        rows=rows,
        preview=preview,
        metadata={},
    )
