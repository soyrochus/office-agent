from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from offagent.domain.models import IndexedItem
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
