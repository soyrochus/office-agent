from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from offagent.domain.models import (
    BlockBundle,
    DocxRun,
    DocxParagraph,
    DocxTableCell,
    DocxTable,
    DocumentBlock,
    DocumentRef,
    IndexedItem,
    SectionPayload,
    StructureSection,
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


@dataclass(frozen=True)
class ResolvedParagraphTarget:
    block_index: int
    paragraph_index: int
    paragraph: Paragraph


@dataclass(frozen=True)
class ResolvedTableCellTarget:
    block_index: int
    table_index: int
    row_index: int
    column_index: int
    table: Table


ResolvedTarget = ResolvedParagraphTarget | ResolvedTableCellTarget


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


def make_table_cell_locator(table_index: int, row_index: int, column_index: int) -> str:
    return f"table:{table_index}:cell:{row_index}:{column_index}"


def parse_table_cell_locator(locator: str) -> tuple[int, int, int]:
    parts = locator.split(":")
    if len(parts) != 5 or parts[0] != "table" or parts[2] != "cell":
        raise InvalidArgumentsError(f"Unsupported DOCX table cell locator: {locator}")
    try:
        table_index = int(parts[1])
        row_index = int(parts[3])
        column_index = int(parts[4])
    except ValueError as exc:
        raise InvalidArgumentsError(f"Invalid DOCX table cell locator: {locator}") from exc
    return table_index, row_index, column_index


def resolve_structure(document_path: Path) -> tuple[StructureSection, ...]:
    document = _open_document(document_path)
    sections: list[StructureSection] = []

    paragraph_index = 0
    table_index = 0
    for block_index, (block_type, block) in enumerate(_iter_blocks(document)):
        if block_type == "paragraph":
            paragraph_model = _paragraph_model(block, block_index, paragraph_index)
            sections.append(
                StructureSection(
                    locator=f"para:{paragraph_index}",
                    section_type="paragraph",
                    preview=paragraph_model.preview,
                    metadata={
                        "block_index": block_index,
                        "block_type": "paragraph",
                        "paragraph_index": paragraph_index,
                        "style_name": paragraph_model.style_name,
                        "is_heading": paragraph_model.is_heading,
                    },
                )
            )
            paragraph_index += 1
            continue

        table_model = _table_model(block, block_index, table_index)
        sections.append(
            StructureSection(
                locator=make_table_cell_locator(table_index, 0, 0),
                section_type="table",
                preview=table_model.preview,
                metadata={
                    "block_index": block_index,
                    "block_type": "table",
                    "table_index": table_index,
                    "row_count": len(table_model.rows),
                    "column_count": max((len(row) for row in table_model.rows), default=0),
                },
            )
        )
        table_index += 1

    return tuple(sections)


def get_section(document_path: Path, locator: str) -> SectionPayload:
    document = _open_document(document_path)
    resolved = _resolve_locator(document, locator)
    document_ref = _document_ref(document_path)

    if isinstance(resolved, ResolvedParagraphTarget):
        paragraph_model = _paragraph_model(
            resolved.paragraph,
            resolved.block_index,
            resolved.paragraph_index,
        )
        return SectionPayload(
            document=document_ref,
            locator=f"para:{resolved.paragraph_index}",
            section_type="paragraph",
            preview=paragraph_model.preview,
            metadata={
                "block_index": resolved.block_index,
                "block_type": "paragraph",
                "paragraph_index": resolved.paragraph_index,
            },
            block_type="paragraph",
            text=paragraph_model.text,
            style_name=paragraph_model.style_name,
            is_heading=paragraph_model.is_heading,
            runs=tuple(_run_model(run) for run in resolved.paragraph.runs),
        )

    table_model = _table_model(resolved.table, resolved.block_index, resolved.table_index)
    cells = tuple(
        DocxTableCell(
            locator=make_table_cell_locator(resolved.table_index, row_index, column_index),
            row_index=row_index,
            column_index=column_index,
            text=cell.text,
            metadata={},
        )
        for row_index, row in enumerate(resolved.table.rows)
        for column_index, cell in enumerate(row.cells)
    )
    return SectionPayload(
        document=document_ref,
        locator=make_table_cell_locator(resolved.table_index, 0, 0),
        section_type="table",
        preview=table_model.preview,
        metadata={
            "block_index": resolved.block_index,
            "block_type": "table",
            "table_index": resolved.table_index,
            "row_count": len(table_model.rows),
            "column_count": max((len(row) for row in table_model.rows), default=0),
        },
        block_type="table",
        rows=table_model.rows,
        table_cells=cells,
    )


def read_node(document_path: Path, locator: str) -> tuple[str, str, dict[str, object]]:
    document = _open_document(document_path)
    resolved = _resolve_locator(document, locator)

    if isinstance(resolved, ResolvedParagraphTarget):
        paragraph_model = _paragraph_model(
            resolved.paragraph,
            resolved.block_index,
            resolved.paragraph_index,
        )
        return (
            "paragraph",
            paragraph_model.text,
            {
                "block_index": resolved.block_index,
                "paragraph_index": resolved.paragraph_index,
                "style_name": paragraph_model.style_name,
                "is_heading": paragraph_model.is_heading,
            },
        )

    cell = resolved.table.rows[resolved.row_index].cells[resolved.column_index]
    return (
        "table_cell",
        cell.text,
        {
            "block_index": resolved.block_index,
            "table_index": resolved.table_index,
            "row_index": resolved.row_index,
            "column_index": resolved.column_index,
        },
    )


def write_node(document_path: Path, locator: str, text: str, output_path: Path | None = None) -> Path:
    document = _open_document(document_path)
    resolved = _resolve_locator(document, locator)

    if isinstance(resolved, ResolvedParagraphTarget):
        return replace_paragraph(document_path, f"para:{resolved.paragraph_index}", text, output_path)

    cell = resolved.table.rows[resolved.row_index].cells[resolved.column_index]
    cell.text = text
    target_path = _target_path(document_path, output_path)
    document.save(target_path)
    return target_path


def insert_paragraph(
    document_path: Path,
    text: str,
    *,
    style_name: str | None = None,
    after_locator: str | None = None,
    output_path: Path | None = None,
) -> tuple[Path, str]:
    if after_locator is None:
        target_path, block_index = append_paragraph_block(
            document_path,
            text,
            style_name=style_name,
            output_path=output_path,
        )
        paragraph_count = len(get_paragraphs(target_path))
        return target_path, f"para:{paragraph_count - 1}"

    document = _open_document(document_path)
    resolved = _resolve_locator(document, after_locator)
    paragraph_index = (
        resolved.paragraph_index + 1
        if isinstance(resolved, ResolvedParagraphTarget)
        else _paragraphs_before_block(document, resolved.block_index)
    )

    anchor_element = (
        resolved.paragraph._element
        if isinstance(resolved, ResolvedParagraphTarget)
        else resolved.table._element
    )
    new_element = document.element.body.add_p()
    anchor_element.addnext(new_element)
    paragraph = Paragraph(new_element, document)
    paragraph.add_run(text)
    if style_name is not None:
        try:
            paragraph.style = style_name
        except (KeyError, ValueError) as exc:
            raise InvalidArgumentsError(f"Unknown DOCX paragraph style: {style_name}") from exc

    target_path = _target_path(document_path, output_path)
    document.save(target_path)
    return target_path, f"para:{paragraph_index}"


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


def get_tables_result(document_path: Path) -> tuple[DocxTable, ...]:
    return get_tables(document_path)


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


def _resolve_locator(document, locator: str) -> ResolvedTarget:
    normalized = locator.strip()
    if normalized.startswith("para:"):
        paragraph_index = _parse_paragraph_locator(normalized)
        current_paragraph_index = 0
        for block_index, (block_type, block) in enumerate(_iter_blocks(document)):
            if block_type != "paragraph":
                continue
            if current_paragraph_index == paragraph_index:
                return ResolvedParagraphTarget(
                    block_index=block_index,
                    paragraph_index=paragraph_index,
                    paragraph=block,
                )
            current_paragraph_index += 1
        raise TargetNotFoundError(f"Paragraph {paragraph_index} does not exist in the document.")

    table_index, row_index, column_index = parse_table_cell_locator(normalized)
    current_table_index = 0
    for block_index, (block_type, block) in enumerate(_iter_blocks(document)):
        if block_type != "table":
            continue
        if current_table_index == table_index:
            try:
                block.rows[row_index].cells[column_index]
            except IndexError as exc:
                raise TargetNotFoundError(
                    f"Table cell {table_index}:{row_index}:{column_index} does not exist."
                ) from exc
            return ResolvedTableCellTarget(
                block_index=block_index,
                table_index=table_index,
                row_index=row_index,
                column_index=column_index,
                table=block,
            )
        current_table_index += 1

    raise TargetNotFoundError(f"Table {table_index} does not exist in the document.")


def _parse_paragraph_locator(locator: str) -> int:
    try:
        return int(locator.split(":", maxsplit=1)[1])
    except ValueError as exc:
        raise InvalidArgumentsError(f"Invalid DOCX paragraph item id: {locator}") from exc


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


def _run_model(run) -> DocxRun:
    color_rgb = None
    if run.font.color.rgb is not None:
        color_rgb = str(run.font.color.rgb)

    font_size = None
    if run.font.size is not None:
        font_size = int(run.font.size)

    return DocxRun(
        text=run.text,
        bold=run.bold,
        italic=run.italic,
        underline=run.underline,
        strike=run.font.strike,
        font_name=run.font.name,
        font_size=font_size,
        color_rgb=color_rgb,
    )


def _paragraphs_before_block(document, block_index: int) -> int:
    count = 0
    for current_block_index, (block_type, _) in enumerate(_iter_blocks(document)):
        if current_block_index > block_index:
            break
        if current_block_index == block_index:
            break
        if block_type == "paragraph":
            count += 1
    return count
