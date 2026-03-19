## Context

This change adds the first end-to-end document workflow on top of the base app foundation. The current project has package structure, configuration, store bootstrap, discovery, and diagnostics, but it does not yet extract document content, populate searchable items, or perform deterministic edits. The DOCX slice is intentionally the first format implementation because `python-docx` exposes the paragraph and run model needed for a narrow MVP while fitting the shared architecture described in `specs/architecture-guidelines.md`.

Constraints:
- Business logic stays in the application service layer; the CLI remains a thin adapter.
- Search must operate through SQLite-backed indexed items, not by scanning `.docx` files at query time.
- The adapter scope is limited to paragraphs; tables, headers, footers, comments, and images remain out of scope.
- Item ids must remain stable across extraction runs as long as paragraph order is unchanged.
- Writes are deterministic and narrow: replace or append one resolved paragraph at a time.

## Goals / Non-Goals

**Goals:**
- Add a DOCX adapter that extracts paragraphs in document order, including empty paragraphs, with `para:{n}` item ids.
- Extend the index layer to persist DOCX document metadata and paragraph items in a form usable by search and locator resolution.
- Add service methods for indexing, reindexing, search, locate, read, replace, and append workflows over DOCX paragraphs.
- Add CLI commands that route those operations through the shared application core.
- Add pytest coverage for extraction, index/search flows, locator resolution, and paragraph patch operations.

**Non-Goals:**
- PowerPoint, Excel, or MCP behavior.
- Versioned output handling beyond the temporary overwrite-or-temp-path behavior allowed by the feature spec.
- Table-aware Word extraction or edits.
- Generic free-form document rewrites, cross-format abstractions beyond what the current DOCX slice needs, or semantic ranking beyond SQLite FTS.

## Decisions

### 1. Implement DOCX behavior in a dedicated adapter module

Decision:
Add `src/offagent/adapters/docx_adapter.py` as the only component that reads or mutates `.docx` files via `python-docx`.

Rationale:
This keeps file-format behavior isolated from the service and interface layers and matches the architecture rule that adapters call their format library directly while the rest of the system works with shared models.

Alternatives considered:
- Put DOCX parsing directly in `app/services.py`.
  Rejected because it would mix use-case orchestration with format-specific mechanics.
- Add a generic extraction framework before implementing DOCX.
  Rejected because the first format path should stay concrete and avoid premature abstraction.

### 2. Treat DOCX paragraphs as the only indexed unit

Decision:
Extract every paragraph in document order, including empty paragraphs, and model each as an item with `item_type="paragraph"` and `item_id="para:{index}"`.

Rationale:
Including empty paragraphs preserves positional stability, which matters for repeatable item ids and deterministic locator resolution. Paragraph-level indexing is also the narrowest useful editing unit for the MVP.

Alternatives considered:
- Skip empty paragraphs to reduce index size.
  Rejected because it would shift downstream paragraph numbers and break item stability.
- Index runs instead of paragraphs.
  Rejected because runs are too formatting-oriented and would complicate search and edits unnecessarily.

### 3. Extend the store with explicit document-item indexing operations

Decision:
Add store helpers for upserting documents, replacing indexed items for a document, and querying FTS-backed paragraph matches joined with document metadata.

Rationale:
The base store currently only bootstraps schema. DOCX support needs explicit persistence boundaries so services can index once and query later without embedding SQL in the CLI or adapter.

Alternatives considered:
- Rebuild the whole database on each index command.
  Rejected because targeted document reindex is already part of the CLI scope.
- Store search text only in memory and skip persistence until later formats exist.
  Rejected because indexed search is a core architectural requirement, not an optional optimization.

### 4. Resolve search, locate, read, and patch through shared services

Decision:
Implement `index_document`, `reindex_document`, `search_corpus`, `resolve_locator`, `read_item`, `replace_item_text`, and `append_item_text` in `app/services.py`, with all file access delegated to the DOCX adapter and all persistence delegated to the store.

Rationale:
This preserves the service layer as the authoritative behavior boundary and allows CLI and future MCP interfaces to share the same workflow logic.

Alternatives considered:
- Add command-specific logic in `interfaces/cli.py`.
  Rejected because it would duplicate core behavior and violate the interface-layer rule.
- Let the adapter query the database directly.
  Rejected because adapters should not own indexing or search behavior.

### 5. Support two locator paths: direct paragraph reference and search-backed item ids

Decision:
Support `locate --paragraph <n>` as direct resolution to `para:{n}`, and use indexed search results plus stored item metadata for search/read/edit flows.

Rationale:
The feature spec needs both deterministic direct lookup and search-driven workflows. Keeping both flows normalized to an `ItemRef` preserves a single patch target model.

Alternatives considered:
- Resolve edits from raw CLI flags without normalizing to `ItemRef`.
  Rejected because it weakens the join between indexed results and patch operations.
- Delay direct locators until a richer locator grammar exists.
  Rejected because paragraph number lookup is a required acceptance criterion.

### 6. Preserve supported formatting by editing paragraph runs narrowly

Decision:
For replace, capture the first run's character formatting, replace the paragraph text, and reapply the first-run formatting to the resulting content. For append, append to the last run when one exists and create a run if the paragraph is empty.

Rationale:
This matches the feature spec while staying within `python-docx`'s paragraph/run model. It gives deterministic behavior without attempting full rich-text fidelity.

Alternatives considered:
- Replace the whole paragraph with plain text and drop formatting.
  Rejected because the spec explicitly preserves first-run formatting on replace.
- Attempt to preserve all run boundaries and styles exactly.
  Rejected because it adds complexity disproportionate to the MVP.

### 7. Add targeted CLI commands rather than a generic mutation interface

Decision:
Expose `index`, `reindex`, `search`, `locate`, `read`, `replace`, and `append` as explicit Typer commands that delegate to service methods.

Rationale:
These commands map directly to the accepted workflows, remain scriptable, and keep user-facing behavior explicit while the product surface is still small.

Alternatives considered:
- Provide one generic `patch` command with operation flags.
  Rejected because the current MVP benefits from a simpler, intention-revealing CLI surface.
- Delay CLI commands and test services only.
  Rejected because the feature includes CLI behavior as part of the contract.

## Risks / Trade-offs

- [DOCX run formatting is lossy when replacing paragraph text] -> Limit the guarantee to preserving the first run's character formatting and cover it with adapter tests.
- [Paragraph-index item ids become stale after users edit the source file outside the tool] -> Reindex on demand and keep the scope limited to deterministic single-file workflows in this feature.
- [FTS-backed search quality may be simplistic for short paragraphs] -> Return preview and locator metadata so users can validate matches before editing.
- [Direct paragraph locators can diverge from stored items if the document changes after indexing] -> Use the source file as the read/write authority and make reindexing an explicit supported path.
- [Introducing `python-docx` expands dependency and fixture complexity] -> Keep the adapter narrow and use a small set of focused DOCX fixtures under pytest.

## Migration Plan

1. Add `python-docx` and the DOCX adapter module.
2. Extend the store with document/item upsert and FTS query operations needed for DOCX indexing and search.
3. Implement service-layer indexing, search, locate, read, replace, and append workflows over DOCX paragraphs.
4. Add Typer commands that call the new services.
5. Add pytest fixtures and tests for extraction, search, locate, read, replace, and append.

Rollback:
Revert the DOCX adapter, CLI commands, and store/service additions. The base app foundation remains intact because this change layers on top of existing modules rather than replacing them.

## Open Questions

- Should `replace` and `append` write in place by default for this feature, or should they always use a temporary output path even before the later versioning feature lands?
- Should empty paragraphs appear in CLI `read` and `search` output exactly as empty strings, or should the presentation layer render them with an explicit placeholder?
- Should `search --doc <file>` filter by source path only, or should it resolve the file to the indexed document id before querying?
