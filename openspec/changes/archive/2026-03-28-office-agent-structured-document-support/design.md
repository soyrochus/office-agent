## Context

Office Agent currently exposes an indexed, item-level workflow built around `AppServices`, per-format adapters, and MCP tools for `index_documents`, `search_documents`, `locate_item`, `read_item`, `replace_text`, `append_text`, and `write_cell`. The indexed identity model is intentionally low-level: DOCX items are paragraphs, PPTX items are text-bearing shapes, and XLSX items are individual cells. That works for search and targeted edits, but it leaves MCP clients responsible for reconstructing document structure from fragments.

This change adds a semantic document layer on top of the existing adapters rather than replacing the index/search path. The new layer must stay deterministic, generic, and composable across DOCX, PPTX, and XLSX, while preserving the current `document_id`-based access model, path-policy enforcement, and versioned write semantics.

## Goals / Non-Goals

**Goals:**

- Add a semantic service layer and MCP surface for structure-aware reads and structured writes across DOCX, PPTX, and XLSX.
- Keep the current indexed `DocumentRef` and `ItemRef` model intact for search, locate, and existing write operations.
- Expose parallel cross-format concepts so clients can inspect structure without format-specific orchestration.
- Compute semantic views deterministically from source documents and indexed document identity, without adding AI or case-specific workflows.
- Reuse existing output-path and policy enforcement rules for semantic write operations.

**Non-Goals:**

- Replacing the current paragraph, shape, or cell indexing model with semantic blocks.
- Adding embedded workflow orchestration, prompt templates, or document-specific business logic inside the MCP server.
- Introducing background synchronization that automatically reindexes outputs after a semantic write.
- Making every format expose identical data shapes where the source formats do not support them naturally.

## Decisions

### 1. Add a semantic service surface in `AppServices` backed by format-specific adapter helpers

Implement new `AppServices` methods for semantic operations such as document structure lookup, slide bundles, workbook snapshots, document blocks, and structured writes. Each method will resolve `document_id` through the existing indexed document registry, enforce path policy, and delegate format-specific extraction or mutation work to the corresponding adapter module.

Rationale:

- `AppServices` is already the orchestration seam shared by CLI and MCP interfaces.
- Keeping semantic orchestration above the adapters preserves the current layering and avoids format branching inside `interfaces/mcp.py`.
- The indexed `document_id` remains the stable entry point even when semantic results are computed directly from the source file.

Alternatives considered:

- Implementing semantic logic directly in MCP tool handlers: rejected because it duplicates path resolution, error mapping, and service orchestration.
- Building one new “semantic adapter” module that handles all formats: rejected because the existing per-format adapters already own source-document parsing rules.

### 2. Represent semantic responses as new domain and MCP transport models instead of overloading `ItemRef`

Add new dataclasses and Pydantic models for semantic outputs, for example document structure summaries, slide bundles, document blocks, paragraph bundles, table snapshots, sheet snapshots, and structured write results. Keep `ItemRef` reserved for indexed editable items and locator-based workflows.

Rationale:

- Semantic responses describe logical units, collections, and write summaries that do not map cleanly to one `item_id`.
- Preserving `ItemRef` semantics avoids breaking existing MCP clients and tests.
- Typed semantic models let the MCP tool schemas stay explicit and machine-readable.

Alternatives considered:

- Packing semantic payloads into `ItemRef.metadata`: rejected because it blurs the contract between indexed items and semantic views.
- Returning untyped dictionaries from MCP tools: rejected because it weakens schema introspection and parity testing.

### 3. Compute semantic reads on demand from source files and avoid persisting semantic projections in SQLite

The new structure and bundle tools should open the source Office document through the existing adapters and assemble semantic results at request time. The index remains responsible for document discovery, identity, search, and stale-target detection, but not for caching slide bundles, block sequences, or workbook snapshots.

Rationale:

- The semantic layer is a higher-level projection over source content, not a new canonical storage model.
- Avoids schema churn in `indexing/store.py` for data that can be derived deterministically.
- Keeps writes and subsequent reads consistent with the actual file on disk rather than a potentially stale semantic cache.

Alternatives considered:

- Persisting semantic structures in SQLite during indexing: rejected because it duplicates source state and adds invalidation complexity.
- Deriving semantic views from indexed items only: rejected because the current index omits notes, tables, and other structure needed by the new tools.

### 4. Use a cross-format structure contract with format-specific detail sections

Define a shared top-level structure model that always identifies the container (`document_id`, file type, display name) and returns a list of logical units. Each unit includes a stable ordinal position, type, preview text, and format-specific metadata. Format-specific tools may expose richer detail, but the base structure contract should make PPTX slides, XLSX sheets, and DOCX blocks comparable at a coarse level.

Rationale:

- This gives clients one generic way to inspect structure before choosing a format-specific tool.
- It preserves the design goal of uniform abstraction without pretending that slides, rows, and paragraphs are literally the same entity.
- Shared fields make MCP schemas easier to learn and easier to test.

Alternatives considered:

- A single fully normalized object model across all formats: rejected because it would erase too much useful format-specific information.
- Only format-specific structure tools with no generic entry point: rejected because it fails the semantic-layer goal of a common abstraction.

### 5. Extend adapters with semantic extraction helpers that preserve source order and native metadata

Each adapter will gain read-oriented helpers beyond the existing indexed-item extraction:

- `docx_adapter`: add ordered block traversal over the document body so paragraphs and tables can be returned in source order, with paragraph style and heading metadata retained.
- `pptx_adapter`: add presentation-level slide summaries plus slide bundle extraction that returns text blocks, notes text, and shape metadata from a specific slide.
- `xlsx_adapter`: add workbook structure and sheet snapshot helpers that return rows or windows in sheet order, with display values and coordinates preserved.

These helpers should remain deterministic and avoid inventing semantic content not present in the file.

Rationale:

- The current `extract_document()` functions are optimized for indexing, not for semantic presentation.
- Source-order traversal is essential for Word blocks and slide/text aggregation.
- Keeping these helpers in adapters localizes library-specific logic to the code that already depends on `python-docx`, `python-pptx`, and `openpyxl`.

Alternatives considered:

- Reassembling semantic units in `AppServices` from low-level indexed items: rejected because important structure is absent from the current index.
- Replacing `extract_document()` with semantic extraction and deriving indexed items from that: rejected because it risks destabilizing the existing search/edit contract.

### 6. Preserve the current write contract by adding structured write methods that still return output-path-based results

Structured write operations such as `append_row`, `write_table`, and `append_paragraph` should follow the existing Office Agent mutation pattern:

- resolve the source document through `document_id`;
- validate the requested logical target in the adapter;
- write to either the original document or a versioned output path according to `output_mode`;
- return a structured result that includes the source document, output path, affected logical target, and a concise summary of what changed.

The service should not automatically refresh the index for new output files; clients can explicitly index or refresh as they do today.

Rationale:

- This keeps semantic writes consistent with existing patch operations and avoids surprising side effects.
- Versioned outputs remain important for safety and for workflows that generate derivative files.
- A structured result gives clients enough information to chain additional actions without requiring immediate reindexing.

Alternatives considered:

- Auto-reindexing written outputs: rejected because it changes the current product contract and can produce unexpected index mutations.
- Returning plain success booleans: rejected because callers need output-path and target details.

### 7. Register each semantic capability as an explicit MCP tool with dedicated request and response schemas

Add tool handlers in `interfaces/mcp.py` for the new semantic operations and corresponding request/response models in `interfaces/mcp_models.py`. Keep the tools generic and composable, for example:

- `get_document_structure`
- `get_presentation_structure`
- `get_slide_bundle`
- `get_slide_notes`
- `get_workbook_structure`
- `get_sheet_snapshot`
- `append_row`
- `write_table`
- `get_document_blocks`
- `get_paragraphs`
- `get_tables`
- `get_block_bundle`
- `append_paragraph`
- `replace_block`

Tool handlers should remain thin wrappers over `AppServices`, using the same validation and error mapping pattern as the existing MCP surface.

Rationale:

- Explicit tool registration preserves discoverability and schema introspection for MCP clients.
- Dedicated request models keep optional fields such as sheet ranges, block indices, and mapping configs validated at the boundary.
- The existing MCP implementation already provides the right pattern for structured result conversion and expected tool error handling.

Alternatives considered:

- One generic `semantic_operation` MCP tool with an action field: rejected because it weakens tool discoverability and schema clarity.
- Exposing only CLI commands first: rejected because the change is specifically about the MCP semantic surface.

## Risks / Trade-offs

- [Semantic reads can diverge from indexed search state if the file changes after indexing] -> Resolve `document_id` through the index but read the current file contents, and document that clients should refresh/reindex when they need search and semantic state to match exactly.
- [DOCX ordered block traversal is more complex than paragraph-only extraction] -> Isolate XML/body-order logic in `docx_adapter` helpers and cover mixed paragraph/table fixtures with focused tests.
- [PPTX notes and bundle extraction may expose non-editable shapes or placeholders inconsistently] -> Restrict bundle output to deterministic metadata and explicitly distinguish editable text blocks from descriptive slide structure.
- [Structured XLSX writes can be ambiguous when callers provide dict-based rows or partial mappings] -> Require explicit header/mapping rules in the request model when the target sheet cannot be inferred unambiguously.
- [Adding many MCP tools increases schema and acceptance-test surface area] -> Centralize model conversion patterns and add parity tests by capability instead of duplicating ad hoc assertions.

## Migration Plan

1. Add new semantic domain models and MCP transport models without changing existing search and write contracts.
2. Extend `AppServices` with semantic read and structured write methods that resolve documents through the current index and path-policy rules.
3. Extend `docx_adapter`, `pptx_adapter`, and `xlsx_adapter` with semantic extraction and mutation helpers.
4. Register the new MCP tools and schemas in `interfaces/mcp.py` and `interfaces/mcp_models.py`.
5. Add focused adapter and service tests for block ordering, slide bundles, notes extraction, sheet snapshots, and structured writes.
6. Add MCP integration and acceptance coverage for the new semantic tool catalog and representative cross-format workflows.

Rollback:

- The change is additive at the API layer, so disabling or removing the new MCP tools is sufficient to roll back behavior.
- No index schema migration is required if semantic projections remain on-demand, which keeps rollback low risk.

## Open Questions

- Should `get_document_structure` be the only generic structure entry point, with format-specific tools treated as detail views, or should generic and format-specific structure tools both be first-class in the final MCP catalog?
- For `write_table`, should dict-based rows require existing header names in the target sheet, or should the first write be allowed to establish headers for an empty region?
- For DOCX `replace_block`, should replacing a table be limited to full-table replacement in the initial version, or should the first release scope it to paragraphs only and keep table mutation read-only?
