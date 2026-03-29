## Context

Office Agent already has a V2 mutation pipeline built around typed locators, shared service dispatch, and per-format object resolvers. Today that pipeline assumes inline structure already exists: `update_object` operates at the object level, `style_inline` works cleanly only when a caller can already address a native run-like child, and each adapter mostly rewrites plain text rather than normalized inline fragments.

That assumption is the main blocker for partial formatting. DOCX, PPTX, and XLSX each represent inline formatting differently, but the user-facing need is the same: mutate a visible character range inside a text-bearing object without first materializing native run structure by hand. The design therefore needs to extend the existing mutation contract, not add a separate partial-formatting tool or a parallel adapter stack.

Constraints that shape the implementation:
- The existing typed locator model in `domain/locators.py` remains the canonical addressing system.
- Existing `create_object`, `update_object`, and `style_inline` callers must keep working unchanged.
- Range semantics must be defined in terms of logical visible text, not native XML/run offsets.
- Unsupported cases must fail explicitly rather than silently degrading formatting or text structure.

## Goals / Non-Goals

**Goals:**
- Add partial inline formatting to the existing V2 mutation surface without introducing a new top-level tool.
- Let `style_inline` target either an existing inline locator or a parent text-bearing object plus a character range.
- Let `update_object` and selected `create_object` flows accept structured text segments so adapters can rebuild native inline structure deterministically.
- Introduce one shared internal fragment model and one shared range-editing algorithm that each format adapter can implement in its own native way.
- Preserve parent/container properties while rewriting inline content and normalize adjacent fragments after every write.

**Non-Goals:**
- Adding substring or fuzzy selector targeting in the first version; explicit character ranges are the only partial-targeting contract.
- Exposing native DOCX runs, PPTX paragraphs, or XLSX rich-text runs as new top-level creation primitives.
- Supporting partial formatting for every XLSX cell type; formulas, numeric cells, booleans, and other non-string targets remain out of scope unless explicitly promoted later.
- Refactoring the broader object-service architecture or replacing the current typed locator system.

## Decisions

### 1. Extend existing tool contracts instead of adding a new partial-formatting tool

`create_object`, `update_object`, and `style_inline` will absorb the new behavior:
- `create_object` remains block/container-oriented, but text-bearing object types may accept optional `segments` for initial inline formatting.
- `update_object` will accept either whole-object text replacement or segment/range-based text rewrites.
- `style_inline` will accept either an existing inline locator or a parent text object locator plus a character range.

Why:
- This keeps the public surface stable and matches the source proposal’s intent.
- Partial formatting is not a separate workflow; it is a more capable form of the mutations users already perform.
- Adding a dedicated “split run” or “format range” tool would leak format-specific inline structure into normal authoring.

Alternative considered:
- Add a dedicated `format_range` or `split_inline` tool.
  Rejected because it would duplicate mutation behavior, increase tool count, and force callers to reason about native inline structure instead of visible text.

### 2. Introduce a shared internal fragment abstraction

The design adds a new internal cross-format representation along these lines:
- `InlineFragment`: `text` plus optional inline style payload.
- `TextContainerSnapshot`: container metadata, full visible text, normalized fragment list, and a stable container kind.
- Shared adapter operations:
  - read a text container as normalized fragments
  - rewrite a text container from fragments
  - split fragments on character boundaries
  - apply inline style to a fragment range
  - normalize adjacent fragments with equivalent formatting

Why:
- All three formats need the same logical edit algorithm even though their native storage differs.
- A shared abstraction keeps range semantics and fragment normalization consistent across formats.
- It localizes format-specific complexity to adapter conversion code instead of scattering it across services and MCP models.

Alternative considered:
- Implement separate range-splitting logic directly in each adapter without a shared model.
  Rejected because the semantics would drift and testing would become format-specific instead of contract-driven.

### 3. Treat visible-text ranges as the canonical partial-targeting model

Partial edits are specified as character offsets within the visible text of a parent text-bearing object. Services do not expose native run indices as the primary contract for partial formatting. Existing inline locators still work, but range-based addressing is defined against the flattened visible text of the target container.

Why:
- It is format-agnostic and user-meaningful.
- It prevents callers from coupling to unstable native segmentation.
- It matches the goal of synthesizing and rewriting inline structure on demand.

Alternative considered:
- Base ranges on native run indices or XML offsets.
  Rejected because those indices are unstable after normalization and differ too much across DOCX, PPTX, and XLSX.

### 4. Keep partial-formatting scope at one logical text container per mutation

Each partial-formatting mutation resolves exactly one text container:
- DOCX: a paragraph
- PPTX: a paragraph inside a text frame
- XLSX: a string/rich-text cell

Range edits do not span multiple containers in a single call.

Why:
- This matches the existing “one resolved object per mutation” rule in the V2 service layer.
- It keeps stale-locator checks and output reindexing unchanged.
- It avoids ambiguous semantics around paragraph breaks, slide shape boundaries, and multi-cell ranges.

Alternative considered:
- Allow shape-wide or multi-paragraph ranges in the first version.
  Rejected because flattening across container boundaries complicates offset mapping and rollback semantics substantially.

### 5. Use adapter-owned promotion and rewrite rules for native inline structures

Each adapter owns how the shared fragment model maps to native structures:
- DOCX: rebuild paragraph runs while preserving paragraph-level style and formatting; reject cases that cannot safely survive run reconstruction.
- PPTX: rebuild runs within one paragraph of a text frame while preserving paragraph properties and shape structure.
- XLSX: treat plain strings and rich text as two storage modes; promote a string cell to rich text only when segment or range-based inline formatting is requested.

Why:
- Native text models differ too much for a shared serializer.
- The adapters already own format-specific write behavior and target validation.
- Promotion-on-demand keeps XLSX complexity contained and avoids forcing rich text on every string cell.

Alternative considered:
- Store a richer intermediate document model above adapters and serialize formats from there.
  Rejected as too large a refactor for this change and not aligned with the current architecture.

### 6. Preserve backward compatibility by making new inputs additive

Existing requests that provide plain text to `create_object` or `update_object`, or existing inline locators to `style_inline`, continue to behave as they do today. New request fields are additive:
- `segments`
- `range`
- optional container-target metadata needed to interpret the range

Validation rules will explicitly reject ambiguous combinations rather than guessing:
- `text` and `segments` together
- parent-range targeting on non-text objects
- partial formatting on unsupported XLSX cell types

Why:
- The current service/MCP stack has broad test coverage and existing callers.
- Additive schema changes minimize migration cost and reduce rollout risk.

Alternative considered:
- Replace current text mutation inputs wholesale with one new structured payload.
  Rejected because it would create unnecessary breakage and complicate phased rollout.

### 7. Keep the service layer as the orchestration boundary

The shared service layer remains responsible for:
- validating mutually exclusive inputs
- resolving locators and ensuring freshness
- dispatching to the correct adapter/object mutation path
- preserving versioned-output and reindex behavior

The services will not implement range-splitting logic themselves. That logic lives behind adapter-level text-container operations.

Why:
- It preserves the existing service responsibilities.
- It keeps format-specific state transitions out of `services.py`.
- It allows the same MCP and non-MCP flows to share one mutation path.

Alternative considered:
- Implement partial-formatting logic inside MCP converters or service methods directly.
  Rejected because it would duplicate adapter concerns and bypass the existing layered architecture.

## Risks / Trade-offs

- `[Run/fragment explosion]` Repeated edits could create excessive native run counts. → Mitigation: normalize adjacent fragments with equivalent formatting after every write and test repeated-edit scenarios.
- `[DOCX/PPTX fidelity loss]` Rebuilding runs may drop unsupported inline artifacts or paragraph internals. → Mitigation: define safe text-container scopes narrowly and reject targets whose native structure cannot be preserved reliably.
- `[XLSX rich text complexity]` openpyxl rich-text support is less mature than full-cell writes. → Mitigation: restrict partial inline formatting to string cells, promote on demand, and fail clearly for unsupported cell states.
- `[Range drift after edits]` character offsets become stale as content changes. → Mitigation: reuse existing stale-locator and one-document-version semantics; each call resolves against the current indexed output only.
- `[Schema ambiguity]` additive request fields can create invalid combinations. → Mitigation: encode mutually exclusive request models and explicit validation in MCP/service schemas rather than interpreting mixed inputs heuristically.

## Migration Plan

1. Add shared internal fragment models and adapter utility interfaces without changing public tool behavior.
2. Extend request models and service validation to accept additive `segments` and `range` inputs behind the existing tool names.
3. Implement format adapters incrementally:
   - DOCX paragraph fragment read/write and range styling
   - PPTX paragraph fragment read/write and range styling
   - XLSX string-cell promotion and rich-text fragment rewriting
4. Add contract tests at adapter, service, and MCP layers for segment replacement, range styling, normalization, and unsupported-target rejection.
5. Roll out with backward-compatible schemas; rollback is straightforward because the change is additive and does not require persisted schema migration.

## Open Questions

- Should the first version of PPTX partial formatting target only paragraph locators, or should a text shape locator implicitly mean its first paragraph when no paragraph child is specified?
- For DOCX paragraphs containing non-text inline content (for example field codes or embedded elements), should the first version reject the paragraph entirely or preserve only a documented safe subset?
- For `update_object`, should `range + text` be supported in the first version, or should the initial implementation limit partial edits to `segments` replacement plus `style_inline` range styling?
- Do we want segment payloads to reuse the existing `InlineStyle` schema directly, or introduce a fragment-specific inline-style payload that can evolve independently from `style_inline`?
