from __future__ import annotations

from dataclasses import replace

from offagent.domain.models import InlineFragment, InlineStyle, VisibleTextRange
from offagent.errors import InvalidArgumentsError


def normalize_fragments(
    fragments: list[InlineFragment] | tuple[InlineFragment, ...],
) -> tuple[InlineFragment, ...]:
    merged: list[InlineFragment] = []
    for fragment in fragments:
        if not fragment.text:
            continue
        if merged and merged[-1].style == fragment.style:
            previous = merged[-1]
            merged[-1] = InlineFragment(text=f"{previous.text}{fragment.text}", style=previous.style)
            continue
        merged.append(fragment)
    return tuple(merged)


def split_fragments_at_offsets(
    fragments: list[InlineFragment] | tuple[InlineFragment, ...],
    offsets: list[int] | tuple[int, ...],
) -> tuple[InlineFragment, ...]:
    normalized_offsets = sorted({offset for offset in offsets if offset > 0})
    if not normalized_offsets:
        return normalize_fragments(fragments)

    split: list[InlineFragment] = []
    current_offset = 0
    offset_index = 0
    for fragment in normalize_fragments(fragments):
        fragment_start = current_offset
        fragment_end = current_offset + len(fragment.text)
        start = 0
        while offset_index < len(normalized_offsets) and normalized_offsets[offset_index] < fragment_end:
            split_at = normalized_offsets[offset_index]
            if split_at > fragment_start:
                relative = split_at - fragment_start
                if relative > start:
                    split.append(InlineFragment(text=fragment.text[start:relative], style=fragment.style))
                start = relative
            offset_index += 1
        if start < len(fragment.text):
            split.append(InlineFragment(text=fragment.text[start:], style=fragment.style))
        current_offset = fragment_end
    return tuple(split)


def validate_visible_text_range(text_range: VisibleTextRange, *, text_length: int) -> None:
    if text_range.start < 0 or text_range.end < 0:
        raise InvalidArgumentsError("Visible-text ranges must use non-negative offsets.")
    if text_range.end <= text_range.start:
        raise InvalidArgumentsError("Visible-text ranges must have end > start.")
    if text_range.end > text_length:
        raise InvalidArgumentsError(
            f"Visible-text range {text_range.start}:{text_range.end} exceeds container length {text_length}."
        )


def apply_style_to_range(
    fragments: list[InlineFragment] | tuple[InlineFragment, ...],
    text_range: VisibleTextRange,
    *,
    style: InlineStyle,
    clear_fields: list[str] | tuple[str, ...],
) -> tuple[InlineFragment, ...]:
    normalized = normalize_fragments(fragments)
    text_length = sum(len(fragment.text) for fragment in normalized)
    validate_visible_text_range(text_range, text_length=text_length)
    split = split_fragments_at_offsets(normalized, (text_range.start, text_range.end))

    updated: list[InlineFragment] = []
    cursor = 0
    for fragment in split:
        next_cursor = cursor + len(fragment.text)
        if cursor >= text_range.start and next_cursor <= text_range.end:
            updated.append(InlineFragment(text=fragment.text, style=merge_inline_style(fragment.style, style, clear_fields)))
        else:
            updated.append(fragment)
        cursor = next_cursor
    return normalize_fragments(updated)


def merge_inline_style(
    base: InlineStyle,
    patch: InlineStyle,
    clear_fields: list[str] | tuple[str, ...],
) -> InlineStyle:
    values = base.__dict__.copy()
    clear_set = set(clear_fields)
    for field_name in clear_set:
        values[field_name] = None
    for field_name, value in patch.__dict__.items():
        if field_name in clear_set:
            continue
        if value is not None:
            values[field_name] = value
    return InlineStyle(**values)


def style_is_empty(style: InlineStyle) -> bool:
    return all(value is None for value in style.__dict__.values())


def fragment_text(
    fragments: list[InlineFragment] | tuple[InlineFragment, ...],
) -> str:
    return "".join(fragment.text for fragment in fragments)


def clone_fragment(fragment: InlineFragment) -> InlineFragment:
    return InlineFragment(text=fragment.text, style=replace(fragment.style))
