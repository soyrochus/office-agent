from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from offagent.domain.models import IndexedItem

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


class TargetNotAppendableError(RuntimeError):
    """Raised when a requested XLSX target cannot accept append text."""


def extract_document(document_path: Path) -> list[IndexedItem]:
    workbook = _open_workbook(document_path)
    items: list[IndexedItem] = []

    for worksheet in workbook.worksheets:
        for row in worksheet.iter_rows():
            for cell in row:
                if not _is_indexable_cell(cell):
                    continue

                item_id = make_item_id(worksheet.title, cell.coordinate)
                formula = _formula_text(cell)
                display_text = _display_text(cell)
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
                        },
                    )
                )

    return items


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
        raise ValueError(f"Unsupported XLSX item id: {item_id}")

    payload = item_id.removeprefix("sheet:")
    if "!" not in payload:
        raise ValueError(f"Invalid XLSX item id: {item_id}")

    sheet_name, coordinate = payload.rsplit("!", maxsplit=1)
    if not sheet_name:
        raise ValueError(f"Invalid XLSX sheet name in item id: {item_id}")
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
        raise LookupError(f"Worksheet {sheet_name!r} does not exist in the workbook.") from exc
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
        raise ValueError("Cell coordinate cannot be empty.")
    if coordinate_to_tuple is None:
        raise RuntimeError("openpyxl is required for XLSX operations.")
    try:
        coordinate_to_tuple(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid XLSX cell coordinate: {coordinate}") from exc
    return normalized


def _target_path(document_path: Path, output_path: Path | None) -> Path:
    return document_path if output_path is None else output_path
