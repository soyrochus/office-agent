## Context

Office Agent has a mature adapter → service → MCP-wrapper pipeline for reading and editing existing DOCX, PPTX, and XLSX documents. The five new tools (`create_document`, `add_content_block`, `style_inline`, `style_block`, `set_structural_role`) must slot into this pipeline without introducing a parallel execution path.

Current state relevant to this change:

- Three format adapters exist at `src/offagent/adapters/{docx,pptx,xlsx}_adapter.py`. Each exposes extract, read, and write functions. Internal `RunFormatting` dataclass already exists in `docx_adapter.py` with the inline style fields.
- Domain models live in `src/offagent/domain/models.py` as frozen dataclasses. `DocxRun` already captures bold/italic/underline/strike/font_name/font_size/color_rgb.
- The canonical locator system (`domain/locators.py`) already covers all target granularities needed: `docx:para:{n}:run:{n}`, `pptx:slide:{n}:shape:{n}`, `xlsx:sheet:{name}!{ref}`.
- `AppServices` in `app/services.py` orchestrates all mutations: resolve output path → call adapter → reindex → return `MutationResult`. Format-specific escape-hatch tools (e.g. `docx_set_paragraph_style`, `pptx_add_slide`) already exist alongside the generic V2 API.
- All MCP tools live in `interfaces/mcp.py`; Pydantic request models in `interfaces/mcp_models.py`; converters in `interfaces/mcp_converters.py`.
- `STYLE` is already a declared `Capability` value in `domain/models.py`; paragraphs and runs already advertise it.

The spec document (`specs/document-creation-and-styling.md`) proposes a `models/`, `adapters/`, `tools/` layout that does not match the actual codebase layout. This design specifies where each piece actually goes.

## Goals / Non-Goals

**Goals:**
- Five new MCP tools with the names and semantics defined in the spec
- Style models (`InlineStyle`, `BlockStyle`) defined at the domain level, shared across formats
- `create_document` integrated with the versioned-output and reindex flow
- DOCX-only guard on `set_structural_role` at the service layer
- Patch semantics for style tools: unspecified fields are left unchanged; explicit null clears a property to library-inherited

**Non-Goals:**
- New top-level module layout (`models/`, `tools/`) — extend existing modules
- Separate `targets.py` — the existing canonical locator system is sufficient
- Markdown/HTML import, template management, chart/media authoring, semantic roles for PPTX/XLSX
- Changes to any existing read/search/edit tools

## Decisions

### 1. Extend existing modules; do not introduce a parallel module tree

The spec proposes `models/styles.py`, `models/targets.py`, `tools/*.py`. The codebase already has `domain/models.py` for shared models, `domain/locators.py` for targeting, `adapters/*_adapter.py` for format logic, `app/services.py` for orchestration, and `interfaces/mcp.py` for tool wrappers.

**Decision:** All new code goes into existing modules. `InlineStyle` and `BlockStyle` are added to `domain/models.py`. Styling/creation adapter functions are added to the existing three adapter files. New service methods are added to `AppServices`. New MCP tools are added to `mcp.py` and `mcp_models.py`.

**Why:** Introducing a parallel tree would create two conventions for the same concern, duplicate the output/reindex plumbing, and make the codebase harder to navigate. The existing structure already handles the separation the spec calls for.

### 2. Style models as frozen dataclasses in domain/models.py

`InlineStyle` and `BlockStyle` will be defined as frozen dataclasses with all fields optional (`T | None`, defaulting to `None`). They mirror the existing `RunFormatting` pattern in `docx_adapter.py`, which will be updated to delegate to `InlineStyle` rather than maintaining a separate definition.

```
@dataclass(frozen=True)
class InlineStyle:
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    strike: bool | None = None
    font_name: str | None = None
    font_size: int | None = None       # half-points for DOCX compatibility
    font_color: str | None = None      # hex RGB string, e.g. "FF0000"
    highlight: str | None = None       # color name where supported (DOCX only)

@dataclass(frozen=True)
class BlockStyle:
    alignment: str | None = None       # "left", "center", "right", "justify"
    indent_level: int | None = None
    left_indent: int | None = None     # EMUs for DOCX/PPTX, integer for XLSX
    right_indent: int | None = None
    spacing_before: int | None = None
    spacing_after: int | None = None
    line_spacing: float | None = None
    wrap_text: bool | None = None      # XLSX only
    vertical_alignment: str | None = None  # XLSX only
    fill_color: str | None = None      # hex RGB; XLSX cell fill
    number_format: str | None = None   # XLSX only
```

**Why:** Frozen dataclasses are the established domain model pattern here. All-optional fields with None = "leave unchanged" is consistent with python-docx's own property semantics (`run.bold = None` means inherit). This avoids a separate sentinel type for "not provided" while keeping the apply function simple: if a field is not None, write it; if None, leave the existing value untouched (patch semantics). Explicit clearing back to inherited is expressed by the service accepting a `clear_fields: list[str]` parameter rather than overloading None.

### 3. create_document does not require a pre-existing document_id

All current service methods take a `document_id` to look up a registered document. `create_document` must instead accept `format` + `output_path` and produce a new file. After writing the empty file it calls `self.show_document(output_path)` — the existing method that indexes a file and returns a `DocumentRef` — to register it in the index.

**Decision:** `create_document(format, output_path, output_mode) -> MutationResult`. Output path is validated against `path_policy` before writing. Returns the new `document_id` and locator (`docx:document`, `pptx:presentation`, `xlsx:workbook`) in `MutationResult`.

**Why:** `show_document` already handles registration + reindex. Reusing it avoids duplicating any index bookkeeping. The output path must still be policy-checked because this creates a file on disk.

### 4. add_content_block as a cross-format service method with a block_type discriminator

Rather than a format-specific escape hatch per block type, `add_content_block` is one service method that dispatches on `(file_type, block_type)`. Supported `block_type` values are a bounded enum, not free-form strings. Format-specific adapter functions are called internally.

Supported pairs:

| format | block_type |
|--------|-----------|
| docx   | paragraph, heading, table |
| pptx   | slide, textbox |
| xlsx   | sheet, row, cell |

Invalid combinations return `InvalidArgumentsError`.

**Why:** A small closed set of block types is more coherent than one method per type (seven methods) and avoids the "one giant tool" anti-pattern. The bounded set also makes tool documentation clear.

### 5. style_inline and style_block follow the existing format-specific escape-hatch pattern

Generic V2 (`update_object`) could in principle carry style properties, but mixing style data into the generic mutation surface blurs the boundary between structural edits and styling. The spec explicitly calls for separate tools.

**Decision:** `style_inline(document_id, locator, style: InlineStyle, clear_fields=[]) -> MutationResult` and `style_block(document_id, locator, style: BlockStyle, clear_fields=[]) -> MutationResult` are new service methods that dispatch on file_type, resolve the target via the existing locator parser, apply styling through the adapter, then call the standard versioned-output + reindex flow.

**Why:** This is exactly the pattern of `docx_set_paragraph_style` — a narrow, named service method with format dispatch. It keeps the generic V2 API clean.

### 6. set_structural_role is guarded at the service layer, not the adapter layer

`set_structural_role` calls `self._require_document_type(document_id, expected="docx", operation="set_structural_role")` before touching any adapter. If the document is PPTX or XLSX the method raises `InvalidArgumentsError` with a clear message. The MCP tool wrapper surfaces this as a `ToolError`.

**Why:** The spec requires a clean error. The service layer is the right place for cross-cutting guards because the adapter layer should not need to know about other formats. `_require_document_type` already exists for this purpose.

### 7. Patch semantics with an explicit clear_fields list

`style_inline` and `style_block` use `None = leave unchanged` for all optional style fields. To explicitly revert a property to inherited (e.g. `run.bold = None` in python-docx), the caller passes `clear_fields=["bold"]`. The service merges the two: first apply non-None values from the style object, then set named fields to None.

**Why:** In JSON/MCP, `null` and "omitted" are both serialised as absent or null, making them indistinguishable at the Pydantic boundary. A separate `clear_fields` list is unambiguous and explicit, consistent with the spec's instruction to "prefer explicit validation over silent no-ops."

## Risks / Trade-offs

- **XLSX rich-text partial styling is speculative** → openpyxl's `InlineFont` supports per-character styling in cells but the API is less tested than full-cell styling. Mitigation: implement full-cell styling first; add rich-text as an additive extension once adapter-level coverage is confirmed. The MCP tool must document which granularity is supported.

- **font_size unit mismatch across formats** → python-docx uses half-points (Pt * 2), python-pptx uses EMUs, openpyxl uses points. Mitigation: `InlineStyle.font_size` is stored as points (float); each adapter converts internally. Document the canonical unit in the model.

- **set_structural_role relies on Word-native styles being present in the document** → Styles like "Heading 1" or "Title" must exist in the document's style catalog. If the document was created with `create_document` (empty document), it may only have "Normal". Mitigation: the DOCX creation adapter seeds the document with the standard Word style set using python-docx's default document template, which includes all standard styles.

- **services.py size** → The file is already 3108 lines. Adding ~5 new methods increases maintenance friction. Mitigation: this is a known trade-off in the existing architecture; the alternative (splitting services.py) is out of scope for this change. New methods follow the existing naming and docstring conventions to keep the file navigable.

- **MCP tool count increase** → Adding 5 tools brings the total from ~51 to ~56. This is within acceptable range per the spec's guidance.

## Migration Plan

No migration required. This is an additive change:

1. Add `InlineStyle` and `BlockStyle` to `domain/models.py`; update `RunFormatting` in `docx_adapter.py` to be an alias or thin wrapper
2. Add styling/creation functions to each adapter file
3. Add five service methods to `AppServices`
4. Add Pydantic request/response models to `mcp_models.py`
5. Add five MCP tool functions to `mcp.py`
6. Add tests

Existing tools, models, and locators are untouched. No index schema changes. No configuration changes.

## Open Questions

- Should `add_content_block` for PPTX `textbox` accept position/size parameters (left, top, width, height) or default to a sensible layout? Current `pptx_add_text_shape` takes explicit coordinates. The spec says "do not push all styling arguments into this tool" — position arguments are structural, not styling, so they likely belong here. Decision deferred to specs artifact.

- Should `create_document` for XLSX accept an initial sheet name, or always create a default sheet named "Sheet1"? Minor but needs a spec-level decision.
