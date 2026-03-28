from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from offagent.domain.models import (
    DocumentRef,
    IndexedItem,
    PresentationSlideSummary,
    PptxTextBlockNode,
    SectionPayload,
    SlideBundle,
    SlideTextBlock,
    StructureSection,
)
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


def build_embedding_text(item: IndexedItem, document_path: Path) -> str:
    del document_path
    return item.content_text


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


def make_slide_locator(slide_number: int) -> str:
    return f"slide:{slide_number}"


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


def resolve_structure(document_path: Path) -> tuple[StructureSection, ...]:
    presentation = _open_presentation(document_path)
    sections: list[StructureSection] = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        text_blocks = _slide_text_blocks(slide)
        preview = next((block.text for block in text_blocks if block.text), "")
        locator = (
            make_item_id(slide_number, text_blocks[0].shape_id)
            if text_blocks
            else make_slide_locator(slide_number)
        )
        sections.append(
            StructureSection(
                locator=locator,
                section_type="slide",
                preview=preview[:120],
                metadata={
                    "slide_number": slide_number,
                    "shape_count": len(slide.shapes),
                    "text_block_count": len(text_blocks),
                },
            )
        )

    return tuple(sections)


def get_section(document_path: Path, locator: str) -> SectionPayload:
    slide_number = _slide_number_from_locator(locator)
    bundle = get_slide_bundle(document_path, slide_number)
    return SectionPayload(
        document=bundle.document,
        locator=locator if locator.startswith("slide:") else make_slide_locator(slide_number),
        section_type="slide",
        preview=bundle.preview,
        metadata=bundle.metadata,
        slide_number=bundle.slide_number,
        notes_text=bundle.notes_text,
        text_blocks=tuple(
            PptxTextBlockNode(
                locator=make_item_id(slide_number, block.shape_id),
                position=block.position,
                shape_id=block.shape_id,
                shape_name=block.shape_name,
                preview=block.preview,
                text=block.text,
                metadata=block.metadata,
            )
            for block in bundle.text_blocks
        ),
    )


def read_node(document_path: Path, locator: str) -> tuple[str, str, dict[str, object]]:
    normalized = locator.strip()
    if normalized.startswith("slide:") and ":shape:" not in normalized:
        slide_number = _slide_number_from_locator(normalized)
        bundle = get_slide_bundle(document_path, slide_number)
        text = "\n\n".join(block.text for block in bundle.text_blocks if block.text)
        return (
            "slide",
            text,
            {
                "slide_number": slide_number,
                "notes_text": bundle.notes_text,
                "text_block_count": len(bundle.text_blocks),
            },
        )

    resolved = resolve_shape(document_path, normalized)
    return (
        "slide_text_shape",
        resolved.text,
        {
            "slide_number": resolved.slide_number,
            "shape_id": resolved.shape_id,
            "shape_index": resolved.shape_index,
            "shape_name": resolved.shape_name,
            "is_placeholder": resolved.is_placeholder,
        },
    )


def write_node(document_path: Path, locator: str, text: str, output_path: Path | None = None) -> Path:
    normalized = locator.strip()
    if normalized.startswith("slide:") and ":shape:" not in normalized:
        shape_locator = _first_text_shape_locator(document_path, _slide_number_from_locator(normalized))
        if shape_locator is None:
            raise TargetNotEditableError("slide has no editable text shapes")
        return replace_text_shape(document_path, shape_locator, text, output_path)
    return replace_text_shape(document_path, normalized, text, output_path)


def get_presentation_structure(document_path: Path) -> tuple[PresentationSlideSummary, ...]:
    presentation = _open_presentation(document_path)
    slides: list[PresentationSlideSummary] = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        text_blocks = _slide_text_blocks(slide)
        preview = next((block.text for block in text_blocks if block.text), "")
        slides.append(
            PresentationSlideSummary(
                slide_number=slide_number,
                preview=preview[:120],
                metadata={
                    "slide_number": slide_number,
                    "shape_count": len(slide.shapes),
                    "text_block_count": len(text_blocks),
                },
            )
        )

    return tuple(slides)


def get_slide_bundle(document_path: Path, slide_number: int) -> SlideBundle:
    presentation = _open_presentation(document_path)
    slide = _resolve_slide(presentation, slide_number)
    text_blocks = _slide_text_blocks(slide)
    preview = next((block.text for block in text_blocks if block.text), "")
    return SlideBundle(
        document=_document_ref(document_path),
        slide_number=slide_number,
        preview=preview[:120],
        notes_text=_notes_text(slide),
        metadata={
            "slide_number": slide_number,
            "shape_count": len(slide.shapes),
            "text_block_count": len(text_blocks),
        },
        text_blocks=tuple(text_blocks),
    )


def get_slide_notes(document_path: Path, slide_number: int) -> str:
    presentation = _open_presentation(document_path)
    slide = _resolve_slide(presentation, slide_number)
    return _notes_text(slide)


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


def _document_ref(document_path: Path) -> DocumentRef:
    resolved_path = document_path.resolve()
    stat = resolved_path.stat()
    return DocumentRef(
        document_id=resolved_path.as_posix(),
        path=resolved_path,
        file_type="pptx",
        display_name=resolved_path.name,
        modified_time=stat.st_mtime,
    )


def _resolve_shape(presentation, item_id: str):
    slide_number, shape_id = parse_item_id(item_id)
    slide = _resolve_slide(presentation, slide_number)

    for shape in slide.shapes:
        if shape.shape_id == shape_id:
            return shape

    raise TargetNotFoundError(f"Shape {shape_id} does not exist on slide {slide_number}.")


def _resolve_slide(presentation, slide_number: int):
    if slide_number < 1:
        raise InvalidArgumentsError(f"Invalid PPTX slide number: {slide_number}")

    try:
        return presentation.slides[slide_number - 1]
    except IndexError as exc:
        raise TargetNotFoundError(
            f"Slide {slide_number} does not exist in the presentation."
        ) from exc


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


def _slide_text_blocks(slide) -> list[SlideTextBlock]:
    blocks: list[SlideTextBlock] = []
    for position, shape in enumerate(slide.shapes):
        if not getattr(shape, "has_text_frame", False):
            continue
        text = _text_frame_text(shape.text_frame)
        blocks.append(
            SlideTextBlock(
                position=position,
                shape_id=shape.shape_id,
                shape_name=getattr(shape, "name", None),
                preview=text[:120],
                text=text,
                metadata={
                    "shape_index": position,
                    "is_placeholder": bool(getattr(shape, "is_placeholder", False)),
                },
            )
        )
    return blocks


def _slide_number_from_locator(locator: str) -> int:
    normalized = locator.strip()
    if normalized.startswith("slide:") and ":shape:" in normalized:
        slide_number, _ = parse_item_id(normalized)
        return slide_number
    parts = normalized.split(":")
    if len(parts) == 2 and parts[0] == "slide":
        try:
            slide_number = int(parts[1])
        except ValueError as exc:
            raise InvalidArgumentsError(f"Invalid slide locator: {locator}") from exc
        if slide_number < 1:
            raise InvalidArgumentsError(f"Invalid PPTX slide number: {slide_number}")
        return slide_number
    raise InvalidArgumentsError(f"Unsupported PPTX locator: {locator}")


def _first_text_shape_locator(document_path: Path, slide_number: int) -> str | None:
    bundle = get_slide_bundle(document_path, slide_number)
    if not bundle.text_blocks:
        return None
    return make_item_id(slide_number, bundle.text_blocks[0].shape_id)


def _notes_text(slide) -> str:
    notes_slide = getattr(slide, "notes_slide", None)
    if notes_slide is None:
        return ""
    text_frame = getattr(notes_slide, "notes_text_frame", None)
    if text_frame is None:
        return ""
    lines = [paragraph.text for paragraph in text_frame.paragraphs if paragraph.text.strip()]
    return "\n".join(lines)
