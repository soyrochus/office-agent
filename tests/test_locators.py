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
