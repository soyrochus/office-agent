from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from offagent.domain.models import IndexedItem
from offagent.errors import InvalidArgumentsError, TargetNotEditableError as BaseTargetNotEditableError
from offagent.errors import TargetNotFoundError

try:
    from pptx import Presentation
except ModuleNotFoundError:  # pragma: no cover - exercised through dependency checks
    Presentation = None


@dataclass(frozen=True)
class ResolvedShape:
    slide_number: int
    shape_id: int
    shape_index: int
    shape_name: str | None
    is_placeholder: bool
    text: str


class TargetNotEditableError(BaseTargetNotEditableError):
    """Raised when a requested PPTX target exists but is not a text frame."""


def extract_document(document_path: Path) -> list[IndexedItem]:
    presentation = _open_presentation(document_path)
    items: list[IndexedItem] = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        for shape_index, shape in enumerate(slide.shapes):
            if not getattr(shape, "has_text_frame", False):
                continue

            item_id = make_item_id(slide_number, shape.shape_id)
            text = _text_frame_text(shape.text_frame)
            items.append(
                IndexedItem(
                    item_id=item_id,
                    item_type="slide_text_shape",
                    locator=item_id,
                    preview=text[:120],
                    content_text=text,
                    metadata={
                        "slide_number": slide_number,
                        "shape_id": shape.shape_id,
                        "shape_index": shape_index,
                        "shape_name": getattr(shape, "name", None),
                        "text_frame_text": text,
                        "is_placeholder": bool(getattr(shape, "is_placeholder", False)),
                    },
                )
            )

    return items


def read_text_shape(document_path: Path, item_id: str) -> str:
    resolved = resolve_shape(document_path, item_id)
    return resolved.text


def replace_text_shape(document_path: Path, item_id: str, text: str, output_path: Path | None = None) -> Path:
    presentation = _open_presentation(document_path)
    shape = _resolve_shape(presentation, item_id)
    text_frame = _require_text_frame(shape)
    text_frame.clear()
    text_frame.paragraphs[0].text = text
    target_path = _target_path(document_path, output_path)
    presentation.save(target_path)
    return target_path


def append_text_shape(document_path: Path, item_id: str, text: str, output_path: Path | None = None) -> Path:
    presentation = _open_presentation(document_path)
    shape = _resolve_shape(presentation, item_id)
    text_frame = _require_text_frame(shape)
    text_frame.text = f"{_text_frame_text(text_frame)}{text}"
    target_path = _target_path(document_path, output_path)
    presentation.save(target_path)
    return target_path


def resolve_shape(document_path: Path, item_id: str) -> ResolvedShape:
    presentation = _open_presentation(document_path)
    shape = _resolve_shape(presentation, item_id)
    text_frame = _require_text_frame(shape)
    slide_number, shape_id = parse_item_id(item_id)
    return ResolvedShape(
        slide_number=slide_number,
        shape_id=shape_id,
        shape_index=_shape_index(shape),
        shape_name=getattr(shape, "name", None),
        is_placeholder=bool(getattr(shape, "is_placeholder", False)),
        text=_text_frame_text(text_frame),
    )


def parse_item_id(item_id: str) -> tuple[int, int]:
    parts = item_id.split(":")
    if len(parts) != 4 or parts[0] != "slide" or parts[2] != "shape":
        raise InvalidArgumentsError(f"Unsupported PPTX item id: {item_id}")

    try:
        slide_number = int(parts[1])
        shape_id = int(parts[3])
    except ValueError as exc:
        raise InvalidArgumentsError(f"Invalid PPTX item id: {item_id}") from exc

    if slide_number < 1:
        raise InvalidArgumentsError(f"Invalid PPTX slide number: {slide_number}")

    return slide_number, shape_id


def make_item_id(slide_number: int, shape_id: int) -> str:
    return f"slide:{slide_number}:shape:{shape_id}"


def _open_presentation(document_path: Path):
    if Presentation is None:
        raise RuntimeError("python-pptx is required for PPTX operations.")
    return Presentation(str(document_path))


def _resolve_shape(presentation, item_id: str):
    slide_number, shape_id = parse_item_id(item_id)

    try:
        slide = presentation.slides[slide_number - 1]
    except IndexError as exc:
        raise TargetNotFoundError(
            f"Slide {slide_number} does not exist in the presentation."
        ) from exc

    for shape in slide.shapes:
        if shape.shape_id == shape_id:
            return shape

    raise TargetNotFoundError(f"Shape {shape_id} does not exist on slide {slide_number}.")


def _require_text_frame(shape):
    if not getattr(shape, "has_text_frame", False):
        raise TargetNotEditableError("target not editable")
    return shape.text_frame


def _text_frame_text(text_frame) -> str:
    return "\n".join(paragraph.text for paragraph in text_frame.paragraphs)


def _shape_index(shape) -> int:
    return shape.element.getparent().index(shape.element)


def _target_path(document_path: Path, output_path: Path | None) -> Path:
    return document_path if output_path is None else output_path
