from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from offagent.adapters import xlsx_adapter
from offagent.domain.locators import parse_locator, to_v2_locator
from offagent.domain.models import Capability, ChildSummary, ObjectPayload
from offagent.errors import InvalidArgumentsError, TargetNotFoundError


@dataclass(frozen=True)
class _XlsxTarget:
    canonical_locator: str
    object_type: str
    sheet_name: str | None = None
    row_index: int | None = None
    column_index: int | None = None
    coordinate: str | None = None
    cell_range: str | None = None
    name: str | None = None


class XlsxObjectResolver:
    def get_object(self, document_path: Path, locator: str) -> ObjectPayload:
        canonical = to_v2_locator(locator, file_type="xlsx")
        workbook = xlsx_adapter._open_workbook(document_path)
        target = _parse_xlsx_target(canonical)

        if target.object_type == "workbook":
            return _build_workbook_payload(document_path, workbook)
        if target.object_type == "worksheet":
            return _build_worksheet_payload(document_path, workbook, target)
        if target.object_type == "row":
            return _build_row_payload(document_path, workbook, target)
        if target.object_type == "column":
            return _build_column_payload(document_path, workbook, target)
        if target.object_type == "cell":
            return _build_cell_payload(document_path, workbook, target)
        if target.object_type == "range":
            return _build_range_payload(document_path, workbook, target)
        if target.object_type == "table":
            return _build_table_payload(document_path, workbook, target)
        if target.object_type == "merged_range":
            return _build_merged_range_payload(document_path, workbook, target)
        if target.object_type == "formula_cell":
            return _build_formula_cell_payload(document_path, workbook, target)
        if target.object_type == "named_range":
            return _build_named_range_payload(document_path, workbook, target)
        raise InvalidArgumentsError(f"Unsupported XLSX locator: {locator}")

    def list_children(
        self,
        document_path: Path,
        locator: str,
        *,
        child_type: str | None = None,
        limit: int | None = None,
    ) -> list[ChildSummary]:
        canonical = to_v2_locator(locator, file_type="xlsx")
        workbook = xlsx_adapter._open_workbook(document_path)
        target = _parse_xlsx_target(canonical)

        if target.object_type == "workbook":
            children = _workbook_children(workbook, child_type=child_type)
        elif target.object_type == "worksheet":
            children = _worksheet_children(workbook, target, child_type=child_type)
        elif target.object_type == "row":
            children = _row_children(workbook, target, child_type=child_type)
        elif target.object_type == "column":
            children = _column_children(workbook, target, child_type=child_type)
        elif target.object_type == "range":
            children = _range_children(workbook, target, child_type=child_type)
        elif target.object_type == "table":
            children = _table_children(workbook, target, child_type=child_type)
        else:
            children = ()

        if limit is not None:
            return list(children[:limit])
        return list(children)

    def resolve_capabilities(self, document_path: Path, locator: str) -> frozenset[Capability]:
        workbook = xlsx_adapter._open_workbook(document_path)
        canonical = to_v2_locator(locator, file_type="xlsx")
        target = _parse_xlsx_target(canonical)
        return _capabilities_for(workbook, target)


def write_range(
    document_path: Path,
    locator: str,
    values: list[list[Any]],
    *,
    output_path: Path,
) -> tuple[str, str, dict[str, Any]]:
    canonical = to_v2_locator(locator, file_type="xlsx")
    workbook = xlsx_adapter._open_workbook(document_path)
    target = _parse_xlsx_target(canonical)
    if target.object_type != "range":
        raise InvalidArgumentsError("xlsx_write_range requires an XLSX range locator.")

    worksheet = _resolve_worksheet(workbook, target)
    min_row, min_col, max_row, max_col = _range_bounds(target.cell_range, canonical)
    expected_rows = max_row - min_row + 1
    expected_cols = max_col - min_col + 1
    if len(values) != expected_rows or any(len(row) != expected_cols for row in values):
        raise InvalidArgumentsError("Value array dimensions do not match the target XLSX range.")

    for row_offset, row in enumerate(values):
        for col_offset, value in enumerate(row):
            worksheet.cell(row=min_row + row_offset, column=min_col + col_offset).value = _coerce_write_value(value)

    workbook.save(output_path)
    return (
        canonical,
        f"Wrote {expected_rows}x{expected_cols} values to {canonical}.",
        {"row_count": expected_rows, "column_count": expected_cols},
    )


def insert_rows(
    document_path: Path,
    locator: str,
    row_number: int,
    count: int,
    *,
    output_path: Path,
) -> tuple[str, str, dict[str, Any]]:
    if row_number < 1 or count < 1:
        raise InvalidArgumentsError("xlsx_insert_rows requires positive row_number and count.")

    canonical = to_v2_locator(locator, file_type="xlsx")
    workbook = xlsx_adapter._open_workbook(document_path)
    target = _parse_xlsx_target(canonical)
    if target.object_type != "worksheet":
        raise InvalidArgumentsError("xlsx_insert_rows requires an XLSX worksheet locator.")

    worksheet = _resolve_worksheet(workbook, target)
    worksheet.insert_rows(row_number, count)
    workbook.save(output_path)
    return (
        f"xlsx:sheet:{worksheet.title}:row:{row_number}",
        f"Inserted {count} rows at {canonical} row {row_number}.",
        {"worksheet_locator": canonical, "row_number": row_number, "count": count},
    )


def insert_columns(
    document_path: Path,
    locator: str,
    column_index: int,
    count: int,
    *,
    output_path: Path,
) -> tuple[str, str, dict[str, Any]]:
    if column_index < 1 or count < 1:
        raise InvalidArgumentsError("xlsx_insert_columns requires positive column_index and count.")

    canonical = to_v2_locator(locator, file_type="xlsx")
    workbook = xlsx_adapter._open_workbook(document_path)
    target = _parse_xlsx_target(canonical)
    if target.object_type != "worksheet":
        raise InvalidArgumentsError("xlsx_insert_columns requires an XLSX worksheet locator.")

    worksheet = _resolve_worksheet(workbook, target)
    worksheet.insert_cols(column_index, count)
    workbook.save(output_path)
    return (
        f"xlsx:sheet:{worksheet.title}:col:{column_index}",
        f"Inserted {count} columns at {canonical} column {column_index}.",
        {"worksheet_locator": canonical, "column_index": column_index, "count": count},
    )


def set_formula(
    document_path: Path,
    locator: str,
    formula: str,
    *,
    output_path: Path,
) -> tuple[str, str, dict[str, Any]]:
    canonical = to_v2_locator(locator, file_type="xlsx")
    workbook = xlsx_adapter._open_workbook(document_path)
    target = _parse_xlsx_target(canonical)
    if target.object_type not in {"cell", "formula_cell"}:
        raise InvalidArgumentsError("xlsx_set_formula requires an XLSX cell locator.")
    if not formula.startswith("=") or len(formula.strip()) <= 1:
        raise InvalidArgumentsError("Invalid XLSX formula; formulas must start with '='.")

    worksheet = _resolve_worksheet(workbook, target)
    cell = _resolve_cell(worksheet, target.coordinate, canonical)
    cell.value = formula
    workbook.save(output_path)
    formula_locator = f"xlsx:sheet:{worksheet.title}:formula_cell:{cell.coordinate}"
    return (
        formula_locator,
        f"Set formula on {formula_locator}.",
        {"formula": formula},
    )


def merge_cells(
    document_path: Path,
    locator: str,
    *,
    output_path: Path,
) -> tuple[str, str, dict[str, Any]]:
    canonical = to_v2_locator(locator, file_type="xlsx")
    workbook = xlsx_adapter._open_workbook(document_path)
    target = _parse_xlsx_target(canonical)
    if target.object_type != "range":
        raise InvalidArgumentsError("xlsx_merge_cells requires an XLSX range locator.")

    worksheet = _resolve_worksheet(workbook, target)
    target_bounds = _range_bounds(target.cell_range, canonical)
    for merged in worksheet.merged_cells.ranges:
        if _ranges_overlap(target_bounds, _range_bounds(str(merged), str(merged))):
            raise InvalidArgumentsError(
                f"Range {target.cell_range} overlaps existing merged range {merged}."
            )

    worksheet.merge_cells(target.cell_range)
    workbook.save(output_path)
    merged_locator = f"xlsx:sheet:{worksheet.title}:merged_range:{target.cell_range}"
    return (
        merged_locator,
        f"Merged cells in {canonical}.",
        {"range": target.cell_range},
    )


def _build_workbook_payload(document_path: Path, workbook) -> ObjectPayload:
    return ObjectPayload(
        document=xlsx_adapter._document_ref(document_path),
        locator="xlsx:workbook",
        object_type="workbook",
        preview=next((worksheet.title for worksheet in workbook.worksheets), ""),
        properties={"sheet_count": len(workbook.worksheets)},
        capabilities=_capability_tuple(workbook, _XlsxTarget("xlsx:workbook", "workbook")),
        child_summary=_workbook_children(workbook),
    )


def _build_worksheet_payload(document_path: Path, workbook, target: _XlsxTarget) -> ObjectPayload:
    worksheet = _resolve_worksheet(workbook, target)
    used_bounds = xlsx_adapter._used_bounds(worksheet)
    return ObjectPayload(
        document=xlsx_adapter._document_ref(document_path),
        locator=target.canonical_locator,
        object_type="worksheet",
        preview=_worksheet_preview(worksheet),
        properties={
            "sheet_name": worksheet.title,
            "used_range": xlsx_adapter._format_range(used_bounds),
            "row_count": 0 if used_bounds is None else used_bounds[2] - used_bounds[0] + 1,
            "column_count": 0 if used_bounds is None else used_bounds[3] - used_bounds[1] + 1,
            "table_count": len(worksheet.tables),
            "merged_range_count": len(worksheet.merged_cells.ranges),
        },
        capabilities=_capability_tuple(workbook, target),
        parent_locator="xlsx:workbook",
        child_summary=_worksheet_children(workbook, target),
    )


def _build_row_payload(document_path: Path, workbook, target: _XlsxTarget) -> ObjectPayload:
    worksheet = _resolve_worksheet(workbook, target)
    assert target.row_index is not None
    used_bounds = xlsx_adapter._used_bounds(worksheet)
    max_col = 0 if used_bounds is None else used_bounds[3]
    row_cells = [worksheet.cell(row=target.row_index, column=column_index) for column_index in range(1, max_col + 1)]
    return ObjectPayload(
        document=xlsx_adapter._document_ref(document_path),
        locator=target.canonical_locator,
        object_type="row",
        preview=" | ".join(xlsx_adapter._display_text(cell) for cell in row_cells if xlsx_adapter._display_text(cell))[:120],
        properties={
            "sheet_name": worksheet.title,
            "row_index": target.row_index,
            "cell_count": len(row_cells),
            "non_empty_cell_count": sum(1 for cell in row_cells if xlsx_adapter._is_indexable_cell(cell)),
        },
        capabilities=_capability_tuple(workbook, target),
        parent_locator=f"xlsx:sheet:{worksheet.title}",
        child_summary=_row_children(workbook, target),
    )


def _build_column_payload(document_path: Path, workbook, target: _XlsxTarget) -> ObjectPayload:
    worksheet = _resolve_worksheet(workbook, target)
    assert target.column_index is not None
    used_bounds = xlsx_adapter._used_bounds(worksheet)
    max_row = 0 if used_bounds is None else used_bounds[2]
    column_cells = [worksheet.cell(row=row_index, column=target.column_index) for row_index in range(1, max_row + 1)]
    return ObjectPayload(
        document=xlsx_adapter._document_ref(document_path),
        locator=target.canonical_locator,
        object_type="column",
        preview=" | ".join(xlsx_adapter._display_text(cell) for cell in column_cells if xlsx_adapter._display_text(cell))[:120],
        properties={
            "sheet_name": worksheet.title,
            "column_index": target.column_index,
            "column_letter": xlsx_adapter.get_column_letter(target.column_index),
            "cell_count": len(column_cells),
            "non_empty_cell_count": sum(1 for cell in column_cells if xlsx_adapter._is_indexable_cell(cell)),
        },
        capabilities=_capability_tuple(workbook, target),
        parent_locator=f"xlsx:sheet:{worksheet.title}",
        child_summary=_column_children(workbook, target),
    )


def _build_cell_payload(document_path: Path, workbook, target: _XlsxTarget) -> ObjectPayload:
    worksheet = _resolve_worksheet(workbook, target)
    cell = _resolve_cell(worksheet, target.coordinate, target.canonical_locator)
    return ObjectPayload(
        document=xlsx_adapter._document_ref(document_path),
        locator=target.canonical_locator,
        object_type="cell",
        preview=xlsx_adapter._display_text(cell)[:120],
        properties={
            "sheet_name": worksheet.title,
            "coordinate": cell.coordinate,
            "value": cell.value,
            "display_value": xlsx_adapter._display_text(cell),
            "formula": xlsx_adapter._formula_text(cell),
            "data_type": cell.data_type,
        },
        capabilities=_capability_tuple(workbook, target),
        parent_locator=f"xlsx:sheet:{worksheet.title}",
    )


def _build_range_payload(document_path: Path, workbook, target: _XlsxTarget) -> ObjectPayload:
    worksheet = _resolve_worksheet(workbook, target)
    min_row, min_col, max_row, max_col = _range_bounds(target.cell_range, target.canonical_locator)
    cells = [
        worksheet.cell(row=row_index, column=column_index)
        for row_index in range(min_row, max_row + 1)
        for column_index in range(min_col, max_col + 1)
    ]
    preview = next((xlsx_adapter._display_text(cell)[:120] for cell in cells if xlsx_adapter._display_text(cell)), "")
    return ObjectPayload(
        document=xlsx_adapter._document_ref(document_path),
        locator=target.canonical_locator,
        object_type="range",
        preview=preview,
        properties={
            "sheet_name": worksheet.title,
            "range": target.cell_range,
            "cell_count": len(cells),
        },
        capabilities=_capability_tuple(workbook, target),
        parent_locator=f"xlsx:sheet:{worksheet.title}",
        child_summary=_range_children(workbook, target),
    )


def _build_table_payload(document_path: Path, workbook, target: _XlsxTarget) -> ObjectPayload:
    worksheet = _resolve_worksheet(workbook, target)
    table = _resolve_table(worksheet, target.name, target.canonical_locator)
    return ObjectPayload(
        document=xlsx_adapter._document_ref(document_path),
        locator=target.canonical_locator,
        object_type="table",
        preview=table.displayName,
        properties={
            "sheet_name": worksheet.title,
            "table_name": table.displayName,
            "range": table.ref,
        },
        capabilities=_capability_tuple(workbook, target),
        parent_locator=f"xlsx:sheet:{worksheet.title}",
        child_summary=_table_children(workbook, target),
    )


def _build_merged_range_payload(document_path: Path, workbook, target: _XlsxTarget) -> ObjectPayload:
    worksheet = _resolve_worksheet(workbook, target)
    merged = _resolve_merged_range(worksheet, target.cell_range, target.canonical_locator)
    return ObjectPayload(
        document=xlsx_adapter._document_ref(document_path),
        locator=target.canonical_locator,
        object_type="merged_range",
        preview=str(merged),
        properties={"sheet_name": worksheet.title, "range": str(merged)},
        capabilities=_capability_tuple(workbook, target),
        parent_locator=f"xlsx:sheet:{worksheet.title}",
    )


def _build_formula_cell_payload(document_path: Path, workbook, target: _XlsxTarget) -> ObjectPayload:
    worksheet = _resolve_worksheet(workbook, target)
    cell = _resolve_cell(worksheet, target.coordinate, target.canonical_locator)
    if xlsx_adapter._formula_text(cell) is None:
        raise TargetNotFoundError(f"Cell {cell.coordinate} does not contain a formula.")
    return ObjectPayload(
        document=xlsx_adapter._document_ref(document_path),
        locator=target.canonical_locator,
        object_type="formula_cell",
        preview=xlsx_adapter._formula_text(cell)[:120],
        properties={
            "sheet_name": worksheet.title,
            "coordinate": cell.coordinate,
            "formula": xlsx_adapter._formula_text(cell),
            "display_value": xlsx_adapter._display_text(cell),
        },
        capabilities=_capability_tuple(workbook, target),
        parent_locator=f"xlsx:sheet:{worksheet.title}",
    )


def _build_named_range_payload(document_path: Path, workbook, target: _XlsxTarget) -> ObjectPayload:
    defined_name = _resolve_named_range(workbook, target.name, target.canonical_locator)
    return ObjectPayload(
        document=xlsx_adapter._document_ref(document_path),
        locator=target.canonical_locator,
        object_type="named_range",
        preview=defined_name.name,
        properties={"name": defined_name.name, "reference": defined_name.attr_text},
        capabilities=_capability_tuple(workbook, target),
        parent_locator="xlsx:workbook",
    )


def _workbook_children(workbook, *, child_type: str | None = None) -> tuple[ChildSummary, ...]:
    if child_type not in {None, "", "worksheet"}:
        return ()
    return tuple(
        ChildSummary(
            locator=f"xlsx:sheet:{worksheet.title}",
            object_type="worksheet",
            preview=_worksheet_preview(worksheet),
            capabilities=_capability_tuple(workbook, _XlsxTarget(f"xlsx:sheet:{worksheet.title}", "worksheet", sheet_name=worksheet.title)),
        )
        for worksheet in workbook.worksheets
    )


def _worksheet_children(workbook, target: _XlsxTarget, *, child_type: str | None = None) -> tuple[ChildSummary, ...]:
    worksheet = _resolve_worksheet(workbook, target)
    normalized_child_type = child_type or None
    children: list[ChildSummary] = []

    used_bounds = xlsx_adapter._used_bounds(worksheet)
    if used_bounds is not None and normalized_child_type in {None, "row"}:
        for row_index in range(used_bounds[0], used_bounds[2] + 1):
            children.append(
                ChildSummary(
                    locator=f"xlsx:sheet:{worksheet.title}:row:{row_index}",
                    object_type="row",
                    preview=_row_preview(worksheet, row_index),
                    capabilities=_capability_tuple(workbook, _XlsxTarget("", "row", sheet_name=worksheet.title, row_index=row_index)),
                )
            )

    if used_bounds is not None and normalized_child_type in {None, "column"}:
        for column_index in range(used_bounds[1], used_bounds[3] + 1):
            children.append(
                ChildSummary(
                    locator=f"xlsx:sheet:{worksheet.title}:col:{column_index}",
                    object_type="column",
                    preview=_column_preview(worksheet, column_index),
                    capabilities=_capability_tuple(workbook, _XlsxTarget("", "column", sheet_name=worksheet.title, column_index=column_index)),
                )
            )

    if normalized_child_type in {None, "table"}:
        for table_name in worksheet.tables:
            children.append(
                ChildSummary(
                    locator=f"xlsx:sheet:{worksheet.title}:table:{table_name}",
                    object_type="table",
                    preview=table_name,
                    capabilities=_capability_tuple(workbook, _XlsxTarget("", "table", sheet_name=worksheet.title, name=table_name)),
                )
            )

    if normalized_child_type in {None, "merged_range"}:
        for merged in worksheet.merged_cells.ranges:
            children.append(
                ChildSummary(
                    locator=f"xlsx:sheet:{worksheet.title}:merged_range:{merged}",
                    object_type="merged_range",
                    preview=str(merged),
                    capabilities=_capability_tuple(workbook, _XlsxTarget("", "merged_range", sheet_name=worksheet.title, cell_range=str(merged))),
                )
            )

    if used_bounds is not None and normalized_child_type in {None, "formula_cell"}:
        for row_index in range(used_bounds[0], used_bounds[2] + 1):
            for column_index in range(used_bounds[1], used_bounds[3] + 1):
                cell = worksheet.cell(row=row_index, column=column_index)
                formula = xlsx_adapter._formula_text(cell)
                if formula is None:
                    continue
                children.append(
                    ChildSummary(
                        locator=f"xlsx:sheet:{worksheet.title}:formula_cell:{cell.coordinate}",
                        object_type="formula_cell",
                        preview=formula[:120],
                        capabilities=_capability_tuple(workbook, _XlsxTarget("", "formula_cell", sheet_name=worksheet.title, coordinate=cell.coordinate)),
                    )
                )

    return tuple(children)


def _row_children(workbook, target: _XlsxTarget, *, child_type: str | None = None) -> tuple[ChildSummary, ...]:
    if child_type not in {None, "", "cell"}:
        return ()
    worksheet = _resolve_worksheet(workbook, target)
    assert target.row_index is not None
    used_bounds = xlsx_adapter._used_bounds(worksheet)
    if used_bounds is None:
        return ()
    return tuple(
        ChildSummary(
            locator=f"xlsx:sheet:{worksheet.title}!{worksheet.cell(row=target.row_index, column=column_index).coordinate}",
            object_type="cell",
            preview=xlsx_adapter._display_text(worksheet.cell(row=target.row_index, column=column_index))[:120],
            capabilities=_capability_tuple(
                workbook,
                _XlsxTarget("", "cell", sheet_name=worksheet.title, coordinate=worksheet.cell(row=target.row_index, column=column_index).coordinate),
            ),
        )
        for column_index in range(used_bounds[1], used_bounds[3] + 1)
    )


def _column_children(workbook, target: _XlsxTarget, *, child_type: str | None = None) -> tuple[ChildSummary, ...]:
    if child_type not in {None, "", "cell"}:
        return ()
    worksheet = _resolve_worksheet(workbook, target)
    assert target.column_index is not None
    used_bounds = xlsx_adapter._used_bounds(worksheet)
    if used_bounds is None:
        return ()
    return tuple(
        ChildSummary(
            locator=f"xlsx:sheet:{worksheet.title}!{worksheet.cell(row=row_index, column=target.column_index).coordinate}",
            object_type="cell",
            preview=xlsx_adapter._display_text(worksheet.cell(row=row_index, column=target.column_index))[:120],
            capabilities=_capability_tuple(
                workbook,
                _XlsxTarget("", "cell", sheet_name=worksheet.title, coordinate=worksheet.cell(row=row_index, column=target.column_index).coordinate),
            ),
        )
        for row_index in range(used_bounds[0], used_bounds[2] + 1)
    )


def _range_children(workbook, target: _XlsxTarget, *, child_type: str | None = None) -> tuple[ChildSummary, ...]:
    if child_type not in {None, "", "cell"}:
        return ()
    worksheet = _resolve_worksheet(workbook, target)
    min_row, min_col, max_row, max_col = _range_bounds(target.cell_range, target.canonical_locator)
    children: list[ChildSummary] = []
    for row_index in range(min_row, max_row + 1):
        for column_index in range(min_col, max_col + 1):
            cell = worksheet.cell(row=row_index, column=column_index)
            children.append(
                ChildSummary(
                    locator=f"xlsx:sheet:{worksheet.title}!{cell.coordinate}",
                    object_type="cell",
                    preview=xlsx_adapter._display_text(cell)[:120],
                    capabilities=_capability_tuple(workbook, _XlsxTarget("", "cell", sheet_name=worksheet.title, coordinate=cell.coordinate)),
                )
            )
    return tuple(children)


def _table_children(workbook, target: _XlsxTarget, *, child_type: str | None = None) -> tuple[ChildSummary, ...]:
    if child_type not in {None, "", "row"}:
        return ()
    worksheet = _resolve_worksheet(workbook, target)
    table = _resolve_table(worksheet, target.name, target.canonical_locator)
    min_row, _, max_row, _ = _range_bounds(table.ref, target.canonical_locator)
    return tuple(
        ChildSummary(
            locator=f"xlsx:sheet:{worksheet.title}:row:{row_index}",
            object_type="row",
            preview=_row_preview(worksheet, row_index),
            capabilities=_capability_tuple(workbook, _XlsxTarget("", "row", sheet_name=worksheet.title, row_index=row_index)),
        )
        for row_index in range(min_row, max_row + 1)
    )


def _resolve_worksheet(workbook, target: _XlsxTarget):
    assert target.sheet_name is not None
    return xlsx_adapter._resolve_worksheet(workbook, target.sheet_name)


def _resolve_cell(worksheet, coordinate: str | None, locator: str):
    if coordinate is None:
        raise InvalidArgumentsError(f"Invalid XLSX locator: {locator}")
    return worksheet[xlsx_adapter._normalize_coordinate(coordinate)]


def _resolve_table(worksheet, table_name: str | None, locator: str):
    if table_name is None:
        raise InvalidArgumentsError(f"Invalid XLSX table locator: {locator}")
    try:
        return worksheet.tables[table_name]
    except KeyError as exc:
        raise TargetNotFoundError(f"Table {table_name!r} does not exist in worksheet {worksheet.title!r}.") from exc


def _resolve_merged_range(worksheet, cell_range: str | None, locator: str):
    if cell_range is None:
        raise InvalidArgumentsError(f"Invalid merged range locator: {locator}")
    for merged in worksheet.merged_cells.ranges:
        if str(merged) == cell_range:
            return merged
    raise TargetNotFoundError(f"Merged range {cell_range!r} does not exist in worksheet {worksheet.title!r}.")


def _resolve_named_range(workbook, name: str | None, locator: str):
    if name is None:
        raise InvalidArgumentsError(f"Invalid named range locator: {locator}")
    defined_name = workbook.defined_names.get(name)
    if defined_name is None:
        raise TargetNotFoundError(f"Named range {name!r} does not exist.")
    return defined_name


def _worksheet_preview(worksheet) -> str:
    first_cell = xlsx_adapter._first_indexable_cell(worksheet)
    return "" if first_cell is None else xlsx_adapter._display_text(first_cell)[:120]


def _row_preview(worksheet, row_index: int) -> str:
    used_bounds = xlsx_adapter._used_bounds(worksheet)
    if used_bounds is None:
        return ""
    return " | ".join(
        xlsx_adapter._display_text(worksheet.cell(row=row_index, column=column_index))
        for column_index in range(used_bounds[1], used_bounds[3] + 1)
        if xlsx_adapter._display_text(worksheet.cell(row=row_index, column=column_index))
    )[:120]


def _column_preview(worksheet, column_index: int) -> str:
    used_bounds = xlsx_adapter._used_bounds(worksheet)
    if used_bounds is None:
        return ""
    return " | ".join(
        xlsx_adapter._display_text(worksheet.cell(row=row_index, column=column_index))
        for row_index in range(used_bounds[0], used_bounds[2] + 1)
        if xlsx_adapter._display_text(worksheet.cell(row=row_index, column=column_index))
    )[:120]


def _range_bounds(cell_range: str | None, locator: str) -> tuple[int, int, int, int]:
    if cell_range is None or xlsx_adapter.range_boundaries is None:
        raise InvalidArgumentsError(f"Invalid XLSX range locator: {locator}")
    min_col, min_row, max_col, max_row = xlsx_adapter.range_boundaries(cell_range)
    return (min_row, min_col, max_row, max_col)


def _ranges_overlap(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> bool:
    return not (
        first[2] < second[0]
        or second[2] < first[0]
        or first[3] < second[1]
        or second[3] < first[1]
    )


def _parse_xlsx_target(locator: str) -> _XlsxTarget:
    parsed = parse_locator(locator)
    components = parsed.components
    if components == ("xlsx", "workbook"):
        return _XlsxTarget(locator, "workbook")
    if len(components) == 3 and components[:2] == ("xlsx", "named_range"):
        return _XlsxTarget(locator, "named_range", name=components[2])
    if len(components) == 3 and components[:2] == ("xlsx", "sheet"):
        return _XlsxTarget(locator, "worksheet", sheet_name=components[2])
    if len(components) == 5 and components[:2] == ("xlsx", "sheet") and components[3] == "row":
        return _XlsxTarget(locator, "row", sheet_name=components[2], row_index=_require_index(components[4], locator))
    if len(components) == 5 and components[:2] == ("xlsx", "sheet") and components[3] == "col":
        return _XlsxTarget(locator, "column", sheet_name=components[2], column_index=_require_index(components[4], locator))
    if len(components) == 4 and components[:2] == ("xlsx", "sheet"):
        coordinate_or_range = components[3]
        if ":" in coordinate_or_range:
            return _XlsxTarget(locator, "range", sheet_name=components[2], cell_range=coordinate_or_range)
        return _XlsxTarget(locator, "cell", sheet_name=components[2], coordinate=coordinate_or_range)
    if len(components) == 5 and components[:2] == ("xlsx", "sheet") and components[3] == "table":
        return _XlsxTarget(locator, "table", sheet_name=components[2], name=components[4])
    if len(components) >= 5 and components[:2] == ("xlsx", "sheet") and components[3] == "merged_range":
        return _XlsxTarget(
            locator,
            "merged_range",
            sheet_name=components[2],
            cell_range=":".join(components[4:]),
        )
    if len(components) == 5 and components[:2] == ("xlsx", "sheet") and components[3] == "formula_cell":
        return _XlsxTarget(locator, "formula_cell", sheet_name=components[2], coordinate=components[4])
    raise InvalidArgumentsError(f"Unsupported XLSX locator: {locator}")


def _capabilities_for(workbook, target: _XlsxTarget) -> frozenset[Capability]:
    if target.object_type == "workbook":
        return frozenset({Capability.READ, Capability.ADD_CHILD})
    if target.object_type == "worksheet":
        capabilities = {Capability.READ, Capability.UPDATE, Capability.ADD_CHILD, Capability.MOVE, Capability.COPY}
        if len(workbook.worksheets) > 1:
            capabilities.add(Capability.DELETE)
        return frozenset(capabilities)
    if target.object_type in {"row", "column", "table"}:
        return frozenset(
            {
                Capability.READ,
                Capability.UPDATE,
                Capability.DELETE,
                Capability.ADD_CHILD,
                Capability.MOVE,
                Capability.COPY,
            }
        )
    if target.object_type in {"cell", "range", "formula_cell"}:
        return frozenset({Capability.READ, Capability.UPDATE, Capability.STYLE})
    if target.object_type == "merged_range":
        return frozenset({Capability.READ, Capability.DELETE, Capability.STYLE})
    if target.object_type == "named_range":
        return frozenset({Capability.READ})
    return frozenset({Capability.READ})


def _capability_tuple(workbook, target: _XlsxTarget) -> tuple[Capability, ...]:
    return tuple(sorted(_capabilities_for(workbook, target), key=lambda capability: capability.value))


def _require_index(raw: str, locator: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise InvalidArgumentsError(f"Invalid XLSX locator: {locator}") from exc


def _coerce_write_value(value: Any) -> Any:
    if isinstance(value, str):
        return xlsx_adapter._coerce_value(value)
    return value
