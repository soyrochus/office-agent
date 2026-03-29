from __future__ import annotations

import pytest

from offagent.domain.models import InlineFragment, InlineStyle, VisibleTextRange
from offagent.domain.text_fragments import apply_style_to_range, normalize_fragments, split_fragments_at_offsets
from offagent.errors import InvalidArgumentsError


def test_normalize_fragments_merges_adjacent_equivalent_styles() -> None:
    fragments = normalize_fragments(
        (
            InlineFragment("Al", InlineStyle(bold=True)),
            InlineFragment("pha", InlineStyle(bold=True)),
            InlineFragment(" ", InlineStyle()),
            InlineFragment("Beta", InlineStyle(italic=True)),
        )
    )

    assert fragments == (
        InlineFragment("Alpha", InlineStyle(bold=True)),
        InlineFragment(" ", InlineStyle()),
        InlineFragment("Beta", InlineStyle(italic=True)),
    )


def test_split_fragments_at_offsets_splits_without_losing_formatting() -> None:
    fragments = split_fragments_at_offsets(
        (InlineFragment("Alphabet", InlineStyle(bold=True)),),
        (2, 5),
    )

    assert fragments == (
        InlineFragment("Al", InlineStyle(bold=True)),
        InlineFragment("pha", InlineStyle(bold=True)),
        InlineFragment("bet", InlineStyle(bold=True)),
    )


def test_apply_style_to_range_updates_only_targeted_characters() -> None:
    fragments = apply_style_to_range(
        (InlineFragment("Alpha Beta", InlineStyle(bold=True)),),
        VisibleTextRange(start=6, end=10),
        style=InlineStyle(italic=True),
        clear_fields=(),
    )

    assert fragments == (
        InlineFragment("Alpha ", InlineStyle(bold=True)),
        InlineFragment("Beta", InlineStyle(bold=True, italic=True)),
    )


def test_apply_style_to_range_rejects_invalid_bounds() -> None:
    with pytest.raises(InvalidArgumentsError, match="end > start"):
        apply_style_to_range(
            (InlineFragment("Alpha", InlineStyle()),),
            VisibleTextRange(start=2, end=2),
            style=InlineStyle(italic=True),
            clear_fields=(),
        )
