from __future__ import annotations

import pytest

from offagent.domain.locators import (
    make_docx_v2_locator,
    make_pptx_v2_locator,
    make_xlsx_v2_locator,
    parse_locator,
    to_legacy_locator,
    to_v2_locator,
)


def test_parse_direct_locator() -> None:
    result = parse_locator("paragraph 17")
    assert result.locator_type == "direct"
    assert result.target_hint == "paragraph"
    assert result.tokens == ("paragraph", "17")
    assert result.file_type == "docx"
    assert result.canonical_locator == "docx:para:17"
    assert result.components == ("docx", "para", "17")
    assert not result.resolved


def test_parse_search_locator() -> None:
    result = parse_locator("the paragraph containing supplier shall")
    assert result.locator_type == "search"
    assert result.target_hint is None
    assert result.tokens == ("the", "paragraph", "containing", "supplier", "shall")
    assert result.file_type is None
    assert result.canonical_locator is None
    assert not result.resolved


def test_parse_pptx_shape_item_id_as_direct_locator() -> None:
    result = parse_locator("slide:2:shape:17")
    assert result.locator_type == "direct"
    assert result.target_hint == "shape"
    assert result.tokens == ("slide:2:shape:17",)
    assert result.file_type == "pptx"
    assert result.canonical_locator == "pptx:slide:2:shape:17"
    assert result.components == ("pptx", "slide", "2", "shape", "17")


def test_parse_pptx_short_shape_locator_as_direct_locator() -> None:
    result = parse_locator("slide:2:17")
    assert result.locator_type == "direct"
    assert result.target_hint == "shape"
    assert result.file_type == "pptx"
    assert result.canonical_locator == "pptx:slide:2:shape:17"
    assert result.components == ("pptx", "slide", "2", "shape", "17")


def test_parse_xlsx_cell_item_id_as_direct_locator() -> None:
    result = parse_locator("sheet:Budget2026!B12")
    assert result.locator_type == "direct"
    assert result.target_hint == "cell"
    assert result.tokens == ("sheet:Budget2026", "B12")
    assert result.file_type == "xlsx"
    assert result.canonical_locator == "xlsx:sheet:Budget2026!B12"
    assert result.components == ("xlsx", "sheet", "Budget2026", "B12")


def test_parse_fully_qualified_docx_table_cell_locator() -> None:
    result = parse_locator("docx:table:1:row:2:cell:3")
    assert result.locator_type == "direct"
    assert result.target_hint == "table_cell"
    assert result.file_type == "docx"
    assert result.canonical_locator == "docx:table:1:row:2:cell:3"
    assert result.components == ("docx", "table", "1", "row", "2", "cell", "3")


def test_parse_fully_qualified_xlsx_range_locator() -> None:
    result = parse_locator("xlsx:sheet:Revenue 2026!B2:D9")
    assert result.locator_type == "direct"
    assert result.target_hint == "range"
    assert result.file_type == "xlsx"
    assert result.canonical_locator == "xlsx:sheet:Revenue 2026!B2:D9"
    assert result.components == ("xlsx", "sheet", "Revenue 2026", "B2:D9")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("para:3", "docx:para:3"),
        ("table:1:cell:2:4", "docx:table:1:row:2:cell:4"),
        ("slide:4", "pptx:slide:4"),
        ("slide:4:shape:9", "pptx:slide:4:shape:9"),
        ("slide:4:9", "pptx:slide:4:shape:9"),
        ("sheet:Revenue!B12", "xlsx:sheet:Revenue!B12"),
        ("docx:para:8", "docx:para:8"),
        ("pptx:slide:4:shape:9", "pptx:slide:4:shape:9"),
        ("xlsx:sheet:Revenue!B12", "xlsx:sheet:Revenue!B12"),
    ],
)
def test_to_v2_locator_round_trip(raw: str, expected: str) -> None:
    assert to_v2_locator(raw) == expected


def test_format_specific_serializers_emit_v2_locators() -> None:
    assert make_docx_v2_locator("table:0:cell:1:2") == "docx:table:0:row:1:cell:2"
    assert make_pptx_v2_locator("slide:7:21") == "pptx:slide:7:shape:21"
    assert make_xlsx_v2_locator("sheet:Notes 2026!A3") == "xlsx:sheet:Notes 2026!A3"


def test_format_specific_serializer_rejects_mismatched_locator() -> None:
    with pytest.raises(ValueError, match="Unsupported docx locator"):
        make_docx_v2_locator("slide:2:shape:5")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("docx:para:8", "para:8"),
        ("docx:table:1:row:2:cell:3", "table:1:cell:2:3"),
        ("pptx:slide:4", "slide:4"),
        ("pptx:slide:4:text_shape:9", "slide:4:shape:9"),
        ("pptx:slide:4:table:9", "slide:4:shape:9"),
        ("xlsx:sheet:Revenue!B12", "sheet:Revenue!B12"),
        ("xlsx:sheet:Revenue:formula_cell:B12", "sheet:Revenue!B12"),
    ],
)
def test_to_legacy_locator_round_trip(raw: str, expected: str) -> None:
    assert to_legacy_locator(raw) == expected
