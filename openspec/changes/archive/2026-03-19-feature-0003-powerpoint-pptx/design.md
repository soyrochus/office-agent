## Context

This change extends the shared Office agent core from one implemented format, DOCX, to a second format with a different structural model: PowerPoint slides and shapes. The current implementation already has indexing, search, direct lookup, read, replace, and append flows for DOCX paragraphs, but those assumptions do not transfer directly to PPTX because the editable unit is a text-bearing shape rather than a paragraph. The design needs to preserve the existing layer boundaries, reuse the shared store and service abstractions where possible, and keep PowerPoint support limited to text-frame shapes in the MVP.

Constraints:
- Business logic stays in the application service layer; the CLI remains a thin adapter.
- Search must continue to operate on indexed items in SQLite FTS5 rather than reading slide content at query time.
- Only shapes with `has_text_frame == True` are in scope for extraction and edits.
- Charts, tables, SmartArt, images, and other non-text shapes must be excluded from indexing and explicitly rejected for edits.
- PPTX item ids must remain stable for a given presentation structure and align with the `slide:{slide_number}:shape:{shape_id}` format from the feature spec.

## Goals / Non-Goals

**Goals:**
- Add a PPTX adapter that traverses slides and extracts only text-bearing shapes with stable item ids and shape metadata.
- Extend the store and service layers to index, search, locate, read, replace, and append PPTX text-frame content.
- Extend CLI commands so the existing indexing and text workflows also support `.pptx`.
- Reject non-editable PowerPoint targets with explicit error handling rather than silently ignoring them.
- Add pytest coverage for PPTX extraction, search, locate, read, replace, and append workflows.

**Non-Goals:**
- Layout manipulation, new slides, or new shapes.
- Notes pages, charts, tables, images, SmartArt, or non-text shapes as editable units.
- Versioned output behavior beyond what the existing product currently does for writes.
- MCP-specific PowerPoint behavior.
- Generalized multi-format abstractions beyond what is needed to cleanly add PPTX beside the current DOCX path.

## Decisions

### 1. Add a dedicated PPTX adapter beside the DOCX adapter

Decision:
Implement `src/offagent/adapters/pptx_adapter.py` as the only component that reads or mutates `.pptx` files via `python-pptx`.

Rationale:
This matches the architecture guideline that adapters isolate format-specific behavior while the service layer owns workflows. It also keeps DOCX and PPTX evolution separate as their document object models differ materially.

Alternatives considered:
- Extend the DOCX adapter with multi-format branches.
  Rejected because it would blur format boundaries and make both adapters harder to reason about.
- Put PPTX traversal logic in the service layer.
  Rejected because it would violate the adapter boundary and duplicate format concerns in workflow code.

### 2. Use text-bearing shapes as the only PPTX indexed unit

Decision:
Index only shapes where `shape.has_text_frame` is true, and represent each extracted item as `item_type="slide_text_shape"` with id `slide:{slide_number}:shape:{shape_id}`.

Rationale:
This matches the MVP scope and keeps extraction aligned with shapes that are both searchable and editable. It also creates a stable mapping between indexed content and later patch operations.

Alternatives considered:
- Index every shape and decide editability later.
  Rejected because non-text shapes would pollute search and complicate user-facing behavior.
- Index slide-level text aggregates only.
  Rejected because edits must target one concrete shape, not an entire slide blob.

### 3. Concatenate text frame paragraphs into one indexed text payload

Decision:
For each editable shape, concatenate its text-frame paragraphs with newline separators for indexing and reading.

Rationale:
This preserves internal text-frame structure enough for readable search previews while still exposing one coherent text payload per shape, which simplifies search, read, replace, and append flows.

Alternatives considered:
- Index each text-frame paragraph as a separate item.
  Rejected because the feature spec targets shapes, not per-paragraph slide fragments.
- Flatten paragraphs without separators.
  Rejected because it loses visible structure and makes read/search output less faithful.

### 4. Extend the store and services with format-aware item handling, not PPTX-specific tables

Decision:
Reuse the existing `documents`, `items`, and `items_fts` structures and extend service logic so PPTX items live beside DOCX items using shared item and search models.

Rationale:
The current store is already format-neutral enough to hold another item type. Reusing it keeps cross-format search support possible later and avoids unnecessary schema branching.

Alternatives considered:
- Add PPTX-specific index tables.
  Rejected because the item schema already captures locator, preview, content text, and metadata.
- Keep PPTX indexing in a separate sidecar file.
  Rejected because it would fragment the shared search substrate.

### 5. Support direct slide lookup and optional shape narrowing

Decision:
Implement `locate --doc <file> --slide <n> [--shape <id>]` so slide-only lookup returns all matching `ItemRef`s for editable text shapes on that slide, and slide-plus-shape returns the specific shape target.

Rationale:
This matches the feature acceptance criteria and respects the structural reality that multiple editable shapes may exist on the same slide.

Alternatives considered:
- Require `--shape` for every locate operation.
  Rejected because the feature explicitly allows slide-only locate.
- Return only the first shape on a slide when `--shape` is omitted.
  Rejected because that would hide ambiguity rather than reporting it.

### 6. Replace and append operate only on text frames and reject non-editable targets explicitly

Decision:
Implement replace and append only for resolved text-frame shapes, and treat non-text shape targets as explicit errors with the “target not editable” behavior from the feature spec.

Rationale:
This keeps writes deterministic and aligns user-facing behavior with the stated exclusions. Explicit rejection is safer than silently coercing or skipping unsupported targets.

Alternatives considered:
- Ignore edit requests for non-text shapes.
  Rejected because silent failure is hard to diagnose and violates the feature contract.
- Attempt best-effort edits on placeholder-like non-text shapes.
  Rejected because the MVP should stay strict about editability rules.

### 7. Replace overwrites the text frame; append extends existing text content

Decision:
For replace, clear the text frame and set the new content on the first paragraph, removing remaining paragraph text. For append, add the provided text to the existing text frame content, respecting any newline supplied by the caller.

Rationale:
This mirrors the feature spec and keeps edits narrow and deterministic within `python-pptx`’s text-frame model.

Alternatives considered:
- Preserve the original paragraph segmentation during replace.
  Rejected because the feature only requires full text-frame replacement, not structural preservation.
- Normalize append to always insert a newline.
  Rejected because the spec leaves newline behavior to the supplied text.

## Risks / Trade-offs

- [PPTX shape identifiers can be less intuitive than shape index positions] -> Store both shape id and index in metadata so locate and debug output remain understandable.
- [Slide-only locate can return multiple editable shapes] -> Return all matching `ItemRef`s for that slide instead of collapsing ambiguity.
- [Some PowerPoint objects may expose partial text semantics differently across presentations] -> Restrict support to `has_text_frame == True` and reject everything else explicitly.
- [Replacing a full text frame loses paragraph-level formatting detail] -> Keep the behavior aligned to the spec and cover it with focused adapter tests.
- [Adding `python-pptx` increases dependency and fixture complexity] -> Keep fixtures small and add only targeted PPTX tests for supported shape cases.

## Migration Plan

1. Add `python-pptx` and the PPTX adapter module.
2. Extend indexing and service logic so `.pptx` files can be indexed and queried beside `.docx`.
3. Add locate, read, replace, and append flows for PPTX text-frame shapes.
4. Extend CLI commands for PPTX-specific lookup arguments and multi-format search.
5. Add pytest fixtures and tests covering extraction, locate ambiguity, non-text rejection, and text-frame patch verification.

Rollback:
Revert the PPTX adapter and the related service/CLI changes. The base app and DOCX support remain intact because PPTX support is additive rather than replacing existing behavior.

## Open Questions

- Should `locate --slide <n>` preserve slide order when returning multiple shape hits, and if so should that be by shape index or shape id?
- Should non-text shapes be rejected only for writes, or should `read` and `locate` also surface them as non-editable errors when explicitly targeted?
- Should the CLI default to mixed-format search results once PPTX is added, or should the README and examples steer users toward explicit `--type` filters until more formats exist?
