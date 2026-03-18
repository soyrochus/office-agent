from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LocatorType = Literal["direct", "search"]

DIRECT_PREFIXES = ("paragraph ", "slide ", "sheet ", "para:", "slide:")


@dataclass(frozen=True)
class LocatorParseResult:
    raw: str
    locator_type: LocatorType
    target_hint: str | None
    tokens: tuple[str, ...]
    resolved: bool = False


def parse_locator(raw: str) -> LocatorParseResult:
    normalized = raw.strip()
    if not normalized:
        raise ValueError("Locator cannot be empty.")

    lowered = normalized.lower()
    locator_type: LocatorType = "direct" if lowered.startswith(DIRECT_PREFIXES) else "search"
    target_hint = _infer_target_hint(lowered)
    tokens = tuple(part for part in normalized.replace("!", " ").split() if part)
    return LocatorParseResult(
        raw=normalized,
        locator_type=locator_type,
        target_hint=target_hint,
        tokens=tokens,
        resolved=False,
    )


def _infer_target_hint(lowered: str) -> str | None:
    if lowered.startswith("paragraph "):
        return "paragraph"
    if lowered.startswith("para:"):
        return "paragraph"
    if lowered.startswith("slide:") and ":shape:" in lowered:
        return "shape"
    if lowered.startswith("slide "):
        return "slide"
    if lowered.startswith("sheet "):
        return "sheet"
    if "cell" in lowered:
        return "cell"
    return None
