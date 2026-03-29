from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from offagent.domain.models import FileType

LocatorType = Literal["direct", "search"]

DIRECT_PREFIXES = (
    "paragraph ",
    "slide ",
    "sheet ",
    "para:",
    "slide:",
    "sheet:",
    "table:",
    "docx:",
    "pptx:",
    "xlsx:",
)
FORMAT_PREFIXES = ("docx:", "pptx:", "xlsx:")


@dataclass(frozen=True)
class LocatorParseResult:
    raw: str
    locator_type: LocatorType
    target_hint: str | None
    tokens: tuple[str, ...]
    resolved: bool = False
    file_type: FileType | None = None
    canonical_locator: str | None = None
    components: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ParsedDirectLocator:
    file_type: FileType
    target_hint: str | None
    canonical_locator: str
    components: tuple[str, ...]


def parse_locator(raw: str) -> LocatorParseResult:
    normalized = raw.strip()
    if not normalized:
        raise ValueError("Locator cannot be empty.")

    lowered = normalized.lower()
    if lowered.startswith(DIRECT_PREFIXES):
        parsed = _parse_direct_locator(normalized)
        return LocatorParseResult(
            raw=normalized,
            locator_type="direct",
            target_hint=parsed.target_hint,
            tokens=_tokenize_legacy_compatible(normalized),
            resolved=False,
            file_type=parsed.file_type,
            canonical_locator=parsed.canonical_locator,
            components=parsed.components,
        )

    return LocatorParseResult(
        raw=normalized,
        locator_type="search",
        target_hint=None,
        tokens=tuple(part for part in normalized.split() if part),
        resolved=False,
        file_type=None,
        canonical_locator=None,
        components=(),
    )


def to_v2_locator(raw: str, *, file_type: FileType | None = None) -> str:
    parsed = parse_locator(raw)
    if parsed.locator_type != "direct":
        raise ValueError(f"Unsupported direct locator: {raw}")
    if file_type is not None and parsed.file_type != file_type:
        raise ValueError(f"Locator {raw!r} does not belong to file type {file_type}.")
    assert parsed.canonical_locator is not None
    return parsed.canonical_locator


def to_legacy_locator(raw: str, *, file_type: FileType | None = None) -> str:
    parsed = parse_locator(raw)
    if parsed.locator_type != "direct":
        raise ValueError(f"Unsupported direct locator: {raw}")
    if file_type is not None and parsed.file_type != file_type:
        raise ValueError(f"Locator {raw!r} does not belong to file type {file_type}.")
    if parsed.file_type is None:
        raise ValueError(f"Unsupported direct locator: {raw}")
    return _to_legacy_from_components(parsed.file_type, parsed.components, raw)


def make_docx_v2_locator(locator: str) -> str:
    return _to_format_locator(locator, expected="docx")


def make_pptx_v2_locator(locator: str) -> str:
    return _to_format_locator(locator, expected="pptx")


def make_xlsx_v2_locator(locator: str) -> str:
    return _to_format_locator(locator, expected="xlsx")


def _to_format_locator(locator: str, *, expected: FileType) -> str:
    parsed = parse_locator(locator)
    if parsed.locator_type != "direct" or parsed.file_type != expected:
        raise ValueError(f"Unsupported {expected} locator: {locator}")
    assert parsed.canonical_locator is not None
    return parsed.canonical_locator


def _to_legacy_from_components(file_type: FileType, components: tuple[str, ...], raw: str) -> str:
    if file_type == "docx":
        if len(components) == 3 and components[:2] == ("docx", "para"):
            return f"para:{components[2]}"
        if (
            len(components) == 7
            and components[:2] == ("docx", "table")
            and components[3] == "row"
            and components[5] == "cell"
        ):
            return f"table:{components[2]}:cell:{components[4]}:{components[6]}"
        raise ValueError(f"Unsupported docx locator for legacy conversion: {raw}")

    if file_type == "pptx":
        if len(components) == 3 and components[:2] == ("pptx", "slide"):
            return f"slide:{components[2]}"
        if len(components) == 5 and components[:2] == ("pptx", "slide"):
            return f"slide:{components[2]}:shape:{components[4]}"
        raise ValueError(f"Unsupported pptx locator for legacy conversion: {raw}")

    if file_type == "xlsx":
        if len(components) == 3 and components[:2] == ("xlsx", "sheet"):
            return f"sheet:{components[2]}"
        if len(components) == 4 and components[:2] == ("xlsx", "sheet"):
            return f"sheet:{components[2]}!{components[3]}"
        if len(components) == 5 and components[:2] == ("xlsx", "sheet") and components[3] == "formula_cell":
            return f"sheet:{components[2]}!{components[4]}"
        raise ValueError(f"Unsupported xlsx locator for legacy conversion: {raw}")

    raise ValueError(f"Unsupported locator conversion for {raw}")


def _parse_direct_locator(raw: str) -> _ParsedDirectLocator:
    lowered = raw.lower()
    if lowered.startswith(FORMAT_PREFIXES):
        return _parse_v2_direct_locator(raw)
    if lowered.startswith("paragraph "):
        return _parse_paragraph_words(raw)
    if lowered.startswith("slide "):
        return _parse_slide_words(raw)
    if lowered.startswith("sheet "):
        return _parse_sheet_words(raw)
    if lowered.startswith("para:"):
        return _parse_docx_locator(raw)
    if lowered.startswith("table:"):
        return _parse_docx_locator(raw)
    if lowered.startswith("slide:"):
        return _parse_pptx_locator(raw)
    if lowered.startswith("sheet:"):
        return _parse_xlsx_locator(raw)
    raise ValueError(f"Unsupported direct locator: {raw}")


def _parse_v2_direct_locator(raw: str) -> _ParsedDirectLocator:
    if raw.startswith("docx:"):
        canonical = raw
        components = tuple(raw.split(":"))
        return _ParsedDirectLocator(
            file_type="docx",
            target_hint=_infer_docx_target_hint(components),
            canonical_locator=canonical,
            components=components,
        )

    if raw.startswith("pptx:"):
        canonical = raw
        components = tuple(raw.split(":"))
        return _ParsedDirectLocator(
            file_type="pptx",
            target_hint=_infer_pptx_target_hint(components),
            canonical_locator=canonical,
            components=components,
        )

    if raw.startswith("xlsx:"):
        canonical = raw
        components = _split_xlsx_components(raw[len("xlsx:") :], include_prefix=True)
        return _ParsedDirectLocator(
            file_type="xlsx",
            target_hint=_infer_xlsx_target_hint(canonical, components),
            canonical_locator=canonical,
            components=components,
        )

    raise ValueError(f"Unsupported fully-qualified locator: {raw}")


def _parse_paragraph_words(raw: str) -> _ParsedDirectLocator:
    paragraph_index = _parse_int(raw.split(maxsplit=1)[1], raw)
    canonical = f"docx:para:{paragraph_index}"
    return _ParsedDirectLocator(
        file_type="docx",
        target_hint="paragraph",
        canonical_locator=canonical,
        components=("docx", "para", str(paragraph_index)),
    )


def _parse_slide_words(raw: str) -> _ParsedDirectLocator:
    slide_number = _parse_int(raw.split(maxsplit=1)[1], raw)
    canonical = f"pptx:slide:{slide_number}"
    return _ParsedDirectLocator(
        file_type="pptx",
        target_hint="slide",
        canonical_locator=canonical,
        components=("pptx", "slide", str(slide_number)),
    )


def _parse_sheet_words(raw: str) -> _ParsedDirectLocator:
    sheet_name = raw.split(maxsplit=1)[1].strip()
    if not sheet_name:
        raise ValueError(f"Invalid worksheet locator: {raw}")
    canonical = f"xlsx:sheet:{sheet_name}"
    return _ParsedDirectLocator(
        file_type="xlsx",
        target_hint="sheet",
        canonical_locator=canonical,
        components=("xlsx", "sheet", sheet_name),
    )


def _parse_docx_locator(raw: str) -> _ParsedDirectLocator:
    if raw.startswith("para:"):
        paragraph_index = _parse_int(raw.split(":", maxsplit=1)[1], raw)
        canonical = f"docx:para:{paragraph_index}"
        return _ParsedDirectLocator(
            file_type="docx",
            target_hint="paragraph",
            canonical_locator=canonical,
            components=("docx", "para", str(paragraph_index)),
        )

    parts = raw.split(":")
    if len(parts) != 5 or parts[0] != "table" or parts[2] != "cell":
        raise ValueError(f"Unsupported DOCX locator: {raw}")
    table_index = _parse_int(parts[1], raw)
    row_index = _parse_int(parts[3], raw)
    column_index = _parse_int(parts[4], raw)
    canonical = f"docx:table:{table_index}:row:{row_index}:cell:{column_index}"
    return _ParsedDirectLocator(
        file_type="docx",
        target_hint="table_cell",
        canonical_locator=canonical,
        components=("docx", "table", str(table_index), "row", str(row_index), "cell", str(column_index)),
    )


def _parse_pptx_locator(raw: str) -> _ParsedDirectLocator:
    parts = raw.split(":")
    if len(parts) == 2 and parts[0] == "slide":
        slide_number = _parse_int(parts[1], raw)
        canonical = f"pptx:slide:{slide_number}"
        return _ParsedDirectLocator(
            file_type="pptx",
            target_hint="slide",
            canonical_locator=canonical,
            components=("pptx", "slide", str(slide_number)),
        )

    if len(parts) == 3 and parts[0] == "slide":
        slide_number = _parse_int(parts[1], raw)
        shape_id = _parse_int(parts[2], raw)
        canonical = f"pptx:slide:{slide_number}:shape:{shape_id}"
        return _ParsedDirectLocator(
            file_type="pptx",
            target_hint="shape",
            canonical_locator=canonical,
            components=("pptx", "slide", str(slide_number), "shape", str(shape_id)),
        )

    if len(parts) == 4 and parts[0] == "slide" and parts[2] == "shape":
        slide_number = _parse_int(parts[1], raw)
        shape_id = _parse_int(parts[3], raw)
        canonical = f"pptx:slide:{slide_number}:shape:{shape_id}"
        return _ParsedDirectLocator(
            file_type="pptx",
            target_hint="shape",
            canonical_locator=canonical,
            components=("pptx", "slide", str(slide_number), "shape", str(shape_id)),
        )

    raise ValueError(f"Unsupported PPTX locator: {raw}")


def _parse_xlsx_locator(raw: str) -> _ParsedDirectLocator:
    remainder = raw[len("sheet:") :]
    if not remainder:
        raise ValueError(f"Invalid worksheet locator: {raw}")

    if "!" in remainder:
        sheet_name, address = remainder.split("!", maxsplit=1)
        if not sheet_name or not address:
            raise ValueError(f"Invalid XLSX locator: {raw}")
        canonical = f"xlsx:sheet:{sheet_name}!{address}"
        return _ParsedDirectLocator(
            file_type="xlsx",
            target_hint="range" if ":" in address else "cell",
            canonical_locator=canonical,
            components=("xlsx", "sheet", sheet_name, address),
        )

    canonical = f"xlsx:sheet:{remainder}"
    return _ParsedDirectLocator(
        file_type="xlsx",
        target_hint="sheet",
        canonical_locator=canonical,
        components=("xlsx", "sheet", remainder),
    )


def _infer_docx_target_hint(components: tuple[str, ...]) -> str | None:
    if len(components) < 2:
        return None
    if "page_break" in components:
        return "page_break"
    if "image" in components:
        return "image"
    if "cell" in components:
        return "table_cell"
    if "row" in components:
        return "table_row"
    if "run" in components:
        return "run"
    kind = components[1]
    if kind == "para":
        return "paragraph"
    if kind in {"document", "section", "table"}:
        return kind
    return _last_named_component(components)


def _infer_pptx_target_hint(components: tuple[str, ...]) -> str | None:
    if len(components) < 2:
        return None
    if "notes" in components:
        return "notes"
    if "cell" in components:
        return "table_cell"
    if "row" in components:
        return "table_row"
    if "group_shape" in components:
        return "group_shape"
    if "text_shape" in components:
        return "text_shape"
    if "image_shape" in components:
        return "image_shape"
    if "shape" in components:
        return "shape"
    kind = components[1]
    if kind in {"presentation", "slide", "table"}:
        return kind
    return _last_named_component(components)


def _infer_xlsx_target_hint(raw: str, components: tuple[str, ...]) -> str | None:
    if len(components) < 2:
        return None
    if components[1] == "workbook":
        return "workbook"
    if components[1] == "named_range":
        return "named_range"
    if components[1] != "sheet":
        return _last_named_component(components)
    if "!" in raw:
        return "range" if ":" in raw.split("!", maxsplit=1)[1] else "cell"
    if "row" in components:
        return "row"
    if "col" in components:
        return "column"
    if "table" in components:
        return "table"
    if "merged_range" in components:
        return "merged_range"
    if "formula_cell" in components:
        return "formula_cell"
    return "sheet"


def _split_xlsx_components(raw: str, *, include_prefix: bool) -> tuple[str, ...]:
    prefix = ("xlsx",) if include_prefix else ()
    if raw == "workbook":
        return prefix + ("workbook",)
    if raw.startswith("named_range:"):
        name = raw.split(":", maxsplit=1)[1]
        return prefix + ("named_range", name)
    if not raw.startswith("sheet:"):
        return prefix + tuple(raw.split(":"))

    remainder = raw[len("sheet:") :]
    if "!" in remainder:
        sheet_name, address = remainder.split("!", maxsplit=1)
        return prefix + ("sheet", sheet_name, address)

    parts = remainder.split(":")
    return prefix + ("sheet",) + tuple(parts)


def _last_named_component(components: tuple[str, ...]) -> str | None:
    for component in reversed(components):
        if component and not component.isdigit():
            return component
    return None


def _tokenize_legacy_compatible(raw: str) -> tuple[str, ...]:
    return tuple(part for part in raw.replace("!", " ").split() if part)


def _parse_int(raw_value: str, locator: str) -> int:
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric locator component in {locator!r}.") from exc
