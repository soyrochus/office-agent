from __future__ import annotations

from offagent.domain.locators import parse_locator


def test_parse_direct_locator() -> None:
    result = parse_locator("paragraph 17")
    assert result.locator_type == "direct"
    assert result.target_hint == "paragraph"
    assert result.tokens == ("paragraph", "17")
    assert not result.resolved


def test_parse_search_locator() -> None:
    result = parse_locator("the paragraph containing supplier shall")
    assert result.locator_type == "search"
    assert result.target_hint is None
    assert not result.resolved


def test_parse_pptx_shape_item_id_as_direct_locator() -> None:
    result = parse_locator("slide:2:shape:17")
    assert result.locator_type == "direct"
    assert result.target_hint == "shape"
    assert result.tokens == ("slide:2:shape:17",)
