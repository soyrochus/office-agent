from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from offagent.domain.models import IndexedItem, XlsxRowEmbedding, XlsxRowEmbeddingCell
from offagent.errors import InvalidArgumentsError, TargetNotEditableError
from offagent.errors import TargetNotFoundError

try:
    from openpyxl import load_workbook
    from openpyxl.utils.cell import coordinate_to_tuple
except ModuleNotFoundError:  # pragma: no cover - exercised through dependency checks
    load_workbook = None
    coordinate_to_tuple = None


@dataclass(frozen=True)
class ResolvedCell:
    sheet_name: str
    coordinate: str
    raw_value: object
    formula: str | None
    display_text: str


class TargetNotAppendableError(TargetNotEditableError):
    """Raised when a requested XLSX target cannot accept append text."""


NUMERIC_TEXT_PATTERN = re.compile(
    r"""
    ^\s*
    [\(\+\-]?
    [$€£]?
    (?:
        \d{1,3}(?:,\d{3})+ |
        \d+
    )
    (?:\.\d+)?
    %?
    \)?
    \s*$
    """,
    re.VERBOSE,
)


def extract_document(document_path: Path) -> list[IndexedItem]:
    workbook = _open_workbook(document_path)
    items: list[IndexedItem] = []

    for worksheet in workbook.worksheets:
        indexed_cells: list[tuple[object, str | None, str]] = []
        row_contexts: dict[int, list[tuple[str, str]]] = {}
        column_contexts: dict[int, list[tuple[str, str]]] = {}

        for row in worksheet.iter_rows():
            for cell in row:
                if not _is_indexable_cell(cell):
                    continue

                formula = _formula_text(cell)
                display_text = _display_text(cell)
                indexed_cells.append((cell, formula, display_text))
                row_contexts.setdefault(cell.row, []).append((cell.coordinate, display_text))
                column_contexts.setdefault(cell.column, []).append((cell.coordinate, display_text))

        for cell, formula, display_text in indexed_cells:
            item_id = make_item_id(worksheet.title, cell.coordinate)
            items.append(
                IndexedItem(
                    item_id=item_id,
                    item_type="cell",
                    locator=item_id,
                    preview=display_text[:120],
                    content_text=display_text,
                    metadata={
                        "sheet_name": worksheet.title,
                        "coordinate": cell.coordinate,
                        "raw_value": cell.value,
                        "formula": formula,
                        "display_text": display_text,
                        "data_type": cell.data_type,
                        "row_context": _context_text(row_contexts[cell.row], exclude=cell.coordinate),
                        "column_context": _context_text(
                            column_contexts[cell.column],
                            exclude=cell.coordinate,
                        ),
                    },
                )
            )

    return items


def build_embedding_text(item: IndexedItem, document_path: Path) -> str:
    metadata = item.metadata
    return "\n".join(
        [
            f"Workbook: {document_path.name}",
            f"Sheet: {metadata.get('sheet_name', '')}",
            f"Cell: {metadata.get('coordinate', '')}",
            f"Row Context: {metadata.get('row_context', '')}",
            f"Column Context: {metadata.get('column_context', '')}",
            f"Value: {metadata.get('display_text', item.content_text)}",
        ]
    )


def build_row_embeddings(items: list[IndexedItem], document_path: Path) -> list[XlsxRowEmbedding]:
    grouped: dict[tuple[str, int], list[IndexedItem]] = {}

    for item in items:
        if not _is_text_like_item(item):
            continue
        metadata = item.metadata
        coordinate = str(metadata.get("coordinate", ""))
        grouped.setdefault(
            (str(metadata.get("sheet_name", "")), _row_number(coordinate)),
            [],
        ).append(item)

    row_embeddings: list[XlsxRowEmbedding] = []
    for (sheet_name, row_number), row_items in sorted(grouped.items()):
        ordered_items = sorted(
            row_items,
            key=lambda item: _coordinate_sort_key(str(item.metadata.get("coordinate", ""))),
        )
        contributing_cells = tuple(
            XlsxRowEmbeddingCell(
                item_id=item.item_id,
                coordinate=str(item.metadata.get("coordinate", "")),
                display_text=str(item.metadata.get("display_text", item.content_text)),
                preview=item.preview,
            )
            for item in ordered_items
        )
        representative = max(
            ordered_items,
            key=lambda item: _representative_score(str(item.metadata.get("coordinate", "")), item),
        )
        row_embeddings.append(
            XlsxRowEmbedding(
                sheet_name=sheet_name,
                row_number=row_number,
                text=_build_row_embedding_text(
                    document_path.name,
                    sheet_name,
                    row_number,
                    contributing_cells,
                ),
                preview=representative.preview,
                representative_item_id=representative.item_id,
                contributing_cells=contributing_cells,
            )
        )

    return row_embeddings


def read_cell(document_path: Path, item_id: str) -> str:
    resolved = resolve_cell(document_path, item_id)
    return resolved.display_text


def write_cell(document_path: Path, item_id: str, value: str, output_path: Path | None = None) -> Path:
    workbook = _open_workbook(document_path)
    cell = _resolve_cell(workbook, item_id)
    cell.value = _coerce_value(value)
    target_path = _target_path(document_path, output_path)
    workbook.save(target_path)
    return target_path


def append_cell(document_path: Path, item_id: str, text: str, output_path: Path | None = None) -> Path:
    workbook = _open_workbook(document_path)
    cell = _resolve_cell(workbook, item_id)
    formula = _formula_text(cell)
    if formula is not None or (cell.value is not None and not isinstance(cell.value, str)):
        raise TargetNotAppendableError("target not appendable; use write-cell")
    if cell.value is None:
        cell.value = text
    else:
        cell.value = f"{cell.value}{text}"
    target_path = _target_path(document_path, output_path)
    workbook.save(target_path)
    return target_path


def resolve_cell(document_path: Path, item_id: str) -> ResolvedCell:
    workbook = _open_workbook(document_path)
    cell = _resolve_cell(workbook, item_id)
    return ResolvedCell(
        sheet_name=cell.parent.title,
        coordinate=cell.coordinate,
        raw_value=cell.value,
        formula=_formula_text(cell),
        display_text=_display_text(cell),
    )


def parse_item_id(item_id: str) -> tuple[str, str]:
    if not item_id.startswith("sheet:"):
        raise InvalidArgumentsError(f"Unsupported XLSX item id: {item_id}")

    payload = item_id.removeprefix("sheet:")
    if "!" not in payload:
        raise InvalidArgumentsError(f"Invalid XLSX item id: {item_id}")

    sheet_name, coordinate = payload.rsplit("!", maxsplit=1)
    if not sheet_name:
        raise InvalidArgumentsError(f"Invalid XLSX sheet name in item id: {item_id}")
    normalized_coordinate = _normalize_coordinate(coordinate)
    return sheet_name, normalized_coordinate


def make_item_id(sheet_name: str, coordinate: str) -> str:
    return f"sheet:{sheet_name}!{_normalize_coordinate(coordinate)}"


def _open_workbook(document_path: Path):
    if load_workbook is None:
        raise RuntimeError("openpyxl is required for XLSX operations.")
    return load_workbook(str(document_path))


def _resolve_cell(workbook, item_id: str):
    sheet_name, coordinate = parse_item_id(item_id)
    try:
        worksheet = workbook[sheet_name]
    except KeyError as exc:
        raise TargetNotFoundError(
            f"Worksheet {sheet_name!r} does not exist in the workbook."
        ) from exc
    return worksheet[coordinate]


def _is_indexable_cell(cell) -> bool:
    return _formula_text(cell) is not None or cell.value is not None


def _formula_text(cell) -> str | None:
    if getattr(cell, "data_type", None) == "f" and cell.value is not None:
        return str(cell.value)
    return None


def _display_text(cell) -> str:
    formula = _formula_text(cell)
    if formula is not None:
        return formula
    return "" if cell.value is None else str(cell.value)


def _coerce_value(value: str) -> object:
    for converter in (int, float):
        try:
            return converter(value)
        except ValueError:
            continue
    return value


def _normalize_coordinate(coordinate: str) -> str:
    normalized = coordinate.strip().upper()
    if not normalized:
        raise InvalidArgumentsError("Cell coordinate cannot be empty.")
    if coordinate_to_tuple is None:
        raise RuntimeError("openpyxl is required for XLSX operations.")
    try:
        coordinate_to_tuple(normalized)
    except ValueError as exc:
        raise InvalidArgumentsError(f"Invalid XLSX cell coordinate: {coordinate}") from exc
    return normalized


def _context_text(entries: list[tuple[str, str]], *, exclude: str) -> str:
    return " | ".join(
        display_text
        for coordinate, display_text in entries
        if coordinate != exclude and display_text
    )


def _target_path(document_path: Path, output_path: Path | None) -> Path:
    return document_path if output_path is None else output_path


def _is_text_like_item(item: IndexedItem) -> bool:
    metadata = item.metadata
    display_text = str(metadata.get("display_text", item.content_text)).strip()
    if not display_text:
        return False

    raw_value = metadata.get("raw_value")
    if metadata.get("formula") is not None:
        return False
    if isinstance(raw_value, bool):
        return False
    if isinstance(raw_value, (int, float)):
        return False
    if NUMERIC_TEXT_PATTERN.match(display_text):
        return False
    return any(character.isalpha() for character in display_text)


def _row_number(coordinate: str) -> int:
    row_number, _ = _coordinate_sort_key(coordinate)
    return row_number


def _coordinate_sort_key(coordinate: str) -> tuple[int, int]:
    normalized = _normalize_coordinate(coordinate)
    if coordinate_to_tuple is None:
        raise RuntimeError("openpyxl is required for XLSX operations.")
    return coordinate_to_tuple(normalized)


def _representative_score(coordinate: str, item: IndexedItem) -> tuple[int, int, int]:
    display_text = str(item.metadata.get("display_text", item.content_text))
    _, column_number = _coordinate_sort_key(coordinate)
    alpha_characters = sum(1 for character in display_text if character.isalpha())
    return (alpha_characters, len(display_text), -column_number)


def _build_row_embedding_text(
    workbook_name: str,
    sheet_name: str,
    row_number: int,
    contributing_cells: tuple[XlsxRowEmbeddingCell, ...],
) -> str:
    lines = [
        f"Workbook: {workbook_name}",
        f"Sheet: {sheet_name}",
        f"Row: {row_number}",
        "Cells:",
    ]
    lines.extend(
        f"- {cell.coordinate}: {cell.display_text}"
        for cell in contributing_cells
    )
    return "\n".join(lines)
