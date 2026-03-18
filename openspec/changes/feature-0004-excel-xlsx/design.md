## Context

This change extends the shared Office agent core from DOCX and PPTX into the third planned document format: Excel workbooks. The current codebase already recognizes `.xlsx` in discovery and the domain model already allows `file_type="xlsx"` plus `write_value` operations, but the implemented indexing and editing pipeline still stops at DOCX and PPTX. `src/offagent/app/services.py` only imports DOCX and PPTX adapters, `INDEXABLE_EXTENSIONS` excludes `.xlsx`, and locate/read/write flows branch only across paragraph and slide-shape behaviors.

Constraints:
- Business logic stays in the application service layer; the CLI remains a thin interface.
- Search must continue to run against SQLite-backed indexed items, not by scanning workbooks at query time.
- The MVP unit of indexing and editing is the worksheet cell, not formulas, tables, or higher-level Excel structures.
- Item ids must stay stable and deterministic using `sheet:{sheet_name}!{coordinate}` so indexed results can be reused for read and patch workflows.
- Writes must be narrow and explicit: direct value replacement for any supported cell, append only for string-compatible cells, and rejection for unsupported append targets.

## Goals / Non-Goals

**Goals:**
- Add an XLSX adapter that traverses worksheets and extracts non-empty cells with stable item ids, locator strings, preview text, and metadata.
- Extend the index layer and service workflows so `.xlsx` documents can be indexed, searched, located, read, and updated beside `.docx` and `.pptx`.
- Add CLI support for Excel-specific lookup and mutation arguments while keeping the same shared application-core flow used by the existing formats.
- Enforce explicit guardrails around append behavior for numeric and formula cells rather than silently coercing unsupported cases.
- Add pytest coverage for extraction, indexing, search, locate, read, write-cell, and guarded append behavior.

**Non-Goals:**
- Formula-aware editing, recalculation policies, or workbook evaluation semantics beyond reading formula text and writing raw cell values.
- Merged-cell semantics, tables, charts, pivot tables, formatting preservation, or worksheet structure edits.
- Versioned output beyond the current write behavior already used by existing format adapters.
- MCP-specific Excel behavior.
- Large abstraction refactors that attempt to unify all document formats before the XLSX slice is working end to end.

## Decisions

### 1. Add a dedicated XLSX adapter module

Decision:
Implement `src/offagent/adapters/xlsx_adapter.py` as the only component that reads or mutates `.xlsx` files via `openpyxl`.

Rationale:
The existing architecture isolates format-specific behavior inside adapters. Excel’s workbook and worksheet model is materially different from DOCX paragraphs and PPTX text frames, so it should live in its own adapter rather than being folded into service logic or existing adapters.

Alternatives considered:
- Add XLSX branches directly inside `app/services.py`.
  Rejected because it would mix workflow orchestration with workbook traversal and mutation logic.
- Create a generic multi-format adapter layer first.
  Rejected because the current codebase already uses one adapter per format, and XLSX can follow that pattern without premature abstraction.

### 2. Treat non-empty cells as the only indexed unit

Decision:
Extract one indexed item per non-empty cell across every worksheet, using `item_type="cell"` and `item_id="sheet:{sheet_name}!{coordinate}"`.

Rationale:
Cell-level indexing is the smallest useful unit for Excel search and deterministic edits. It matches the intended locate and write workflows and gives one stable target per sheet/cell coordinate without introducing row, range, or formula-graph complexity.

Alternatives considered:
- Index entire worksheets as one text blob.
  Rejected because it would make locate, read, and write-cell operations too coarse.
- Index rows instead of cells.
  Rejected because search hits would still need a second resolution step to identify the editable cell.

### 3. Persist both display text and structural metadata for each cell

Decision:
Populate indexed XLSX items with sheet name, coordinate, raw value, and formula metadata, and use a stringified display representation as the searchable `content_text`.

Rationale:
Search needs a text payload, while locate/read/write workflows need structural metadata to resolve exact workbook positions. Storing both keeps the shared `items` and `items_fts` tables sufficient for Excel without introducing XLSX-specific tables.

Alternatives considered:
- Store only the display string and infer structure later from item ids.
  Rejected because direct lookup, debugging, and future output formatting benefit from explicit metadata fields.
- Store formulas only as metadata and exclude them from search.
  Rejected because formula text is part of the workbook content the user may need to find.

### 4. Extend shared services with XLSX-aware branches rather than separate service APIs

Decision:
Keep indexing, search, locate, read, and patch workflows in `AppServices`, but extend `_extract_items`, `INDEXABLE_EXTENSIONS`, validation helpers, and the locate/read/write branches so `.xlsx` documents behave as a first-class supported format.

Rationale:
The service layer is already the workflow boundary for DOCX and PPTX. Reusing it preserves one core path for CLI and future MCP interfaces and lets Excel support slot into the existing persistence and patch pipeline.

Alternatives considered:
- Add an Excel-only service class.
  Rejected because it would fragment cross-format orchestration for little gain.
- Make the CLI call the XLSX adapter directly.
  Rejected because it would bypass indexing and shared error handling patterns already established in the app layer.

### 5. Use explicit sheet-and-cell lookup for direct locate

Decision:
Implement Excel direct lookup as `locate --doc <file> --sheet <name> --cell <coordinate>`, resolving to exactly one indexed `ItemRef` by normalized item id.

Rationale:
This aligns with the planned Excel UX and fits the deterministic cell model better than search-style free-form locators. It also complements the existing `locators.py` hinting for sheet/cell-oriented direct locators without overloading DOCX and PPTX lookup paths.

Alternatives considered:
- Reuse paragraph/slide locator flags and parse Excel locations from free text only.
  Rejected because explicit `--sheet` and `--cell` arguments are clearer and easier to validate.
- Allow sheet-only locate to return whole ranges or multiple cells.
  Rejected because the MVP editing target is one concrete cell at a time.

### 6. Separate overwrite and append semantics for cells

Decision:
Add a direct `write-cell` flow that sets `cell.value` with light type coercion, and keep `append` as a restricted operation that only succeeds for empty or string-compatible cells.

Rationale:
Excel cells carry stronger value semantics than paragraphs or text frames. Splitting overwrite from append keeps the normal spreadsheet mutation path explicit and avoids ambiguous behavior on numeric or formula cells.

Alternatives considered:
- Treat append as string concatenation for every cell type.
  Rejected because it would silently destroy numeric or formula meaning.
- Support only `write-cell` and drop append for XLSX.
  Rejected because the repo’s Excel scope already includes guarded append behavior for compatible cells.

### 7. Add `openpyxl` as the new external dependency and test against workbook fixtures

Decision:
Introduce `openpyxl` for workbook inspection and updates, and add focused XLSX fixtures that cover multiple sheets, plain values, strings, numbers, and formulas.

Rationale:
The project already uses one format library per Office type. `openpyxl` is the natural workbook object model for the supported scope, and focused fixtures are necessary to validate extraction and mutation semantics that differ from DOCX and PPTX.

Alternatives considered:
- Generate XLSX XML manually.
  Rejected because it is brittle and outside the project’s current library-based architecture.
- Delay fixture coverage until after implementation.
  Rejected because append restrictions and formula handling are precisely the areas most likely to regress without tests.

## Risks / Trade-offs

- [Cell ids become stale if users restructure sheets outside the tool after indexing] -> Keep the workbook file as the read/write authority and make reindexing the supported recovery path.
- [Stringifying numeric, date, and formula values for search may not exactly match Excel display formatting] -> Index a deterministic string representation and keep the scope limited to searchability, not UI-faithful rendering.
- [Appending to cells can blur the line between text editing and spreadsheet data mutation] -> Restrict append to empty or string-compatible cells and reject unsupported targets explicitly.
- [`openpyxl` adds dependency and fixture complexity] -> Keep the adapter narrowly scoped and use a small set of stable workbook fixtures for verification.
- [Direct lookup becomes case-sensitive or naming-sensitive around sheet titles] -> Normalize sheet-name handling consistently in the adapter and CLI validation, and cover it in tests.

## Migration Plan

1. Add `openpyxl` to project dependencies and create `src/offagent/adapters/xlsx_adapter.py`.
2. Extend indexing helpers and service validation so `.xlsx` is treated as an indexable format.
3. Implement XLSX extraction plus read, write-cell, and guarded append operations in the adapter.
4. Extend shared service methods and CLI commands for Excel locate, search, read, and mutation workflows.
5. Add XLSX fixtures and pytest coverage for extraction, search, locate, read, overwrite, and append rejection cases.

Rollback:
Revert the XLSX adapter, dependency addition, and related service/CLI/test changes. Existing DOCX and PPTX support remains intact because XLSX support is additive.

## Open Questions

- Should `write-cell` preserve native numeric and boolean types when values are passed as strings from the CLI, or should the initial implementation always write strings unless an explicit typed flag is added later?
- Should formula cells be readable and searchable by both the formula text and the cached value when present, or only by the formula text for deterministic behavior?
- Should direct locate normalize sheet names case-insensitively at the CLI layer, or require exact workbook title matches from the start?
