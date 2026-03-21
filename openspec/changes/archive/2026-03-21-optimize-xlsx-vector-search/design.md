## Context

XLSX indexing currently extracts one `IndexedItem` per populated cell in `src/offagent/adapters/xlsx_adapter.py`, persists those cell items in `items`, and generates one embedding per item in `AppServices.index_document()`. That keeps semantic hit resolution simple because each embedding already maps to a single cell `storage_id`, but it is a poor fit for spreadsheet-shaped content where many populated cells are numeric-only or otherwise low-value for semantic retrieval.

The current adapter already captures sheet name, coordinate, display text, and row/column context in item metadata, and `build_embedding_text()` formats that context into the text sent to the embedding provider. The store layer also already has vector-side tables (`item_embeddings`, `embedding_meta`) separate from the canonical `items` and `items_fts` tables. This change should therefore optimize only the XLSX semantic path: keep the existing cell item index, locators, read/write flows, and keyword search behavior unchanged while replacing XLSX vector generation and lookup with row-oriented records that can still resolve back to real cells.

The design matters because the change crosses the adapter layer, service layer, and index store schema, and because it alters the identity used by the semantic path without changing the editable identity model used everywhere else.

## Goals / Non-Goals

**Goals:**

- Reduce XLSX embedding volume by generating embeddings only for text-bearing worksheet rows instead of every populated cell.
- Filter out empty, numeric-only, and other non-text-like XLSX cells from semantic embedding inputs.
- Preserve enough row-to-cell metadata that semantic and hybrid search can still return actionable workbook locations.
- Keep existing cell-level `IndexedItem` persistence and XLSX keyword search semantics unchanged.
- Make the row-level vector representation explicit in storage so reindexing, search, and future diagnostics can reason about it deterministically.

**Non-Goals:**

- Changing DOCX or PPTX embedding construction.
- Changing the editable unit away from the current cell-level XLSX `item_id`.
- Reworking keyword search ranking or the `items_fts` schema.
- Introducing approximate nearest-neighbor infrastructure or a separate vector database.
- Adding workbook-wide aggregation beyond row granularity in this change.

## Decisions

### 1. Keep cell-level indexing as the canonical XLSX document model and add a separate row-level semantic model

`extract_document()` should continue to emit one `IndexedItem` per populated cell, with the same `item_id`, `locator`, and metadata shape needed by read/write operations and keyword search. XLSX semantic indexing will instead derive a second, search-only representation from those extracted cells: one embedding candidate per worksheet row.

Each row candidate should retain:
- workbook and sheet identifiers;
- the row number;
- the formatted text used for embedding;
- an ordered list of contributing cell references and their display values.

Why this approach:
- It isolates the optimization to the vector path and avoids destabilizing editing, display, or FTS behavior.
- It matches the product requirement that hits still resolve to real workbook cells even though the embedding unit changes.

Alternatives considered:
- Replacing cell items entirely with row items. Rejected because it would break existing XLSX locator semantics and keyword search granularity.
- Keeping one embedding per cell and only filtering numeric cells. Rejected because large spreadsheets would still produce too many embeddings and duplicated row context.

### 2. Define “text-bearing row” as a row with at least one semantically useful cell, and embed one structured row summary

Introduce XLSX-specific semantic grouping logic that scans extracted cell items and groups them by `(sheet_name, row_number)`. Within each row, only cells whose display text is text-like should contribute to the row summary and the vector mapping. Numeric-only values, empty strings, and formula/display values that normalize to non-informative text should be excluded.

The embedded row text should be a deterministic structured block containing:
- workbook name;
- sheet name;
- row number;
- concise per-cell entries such as coordinate plus display text;
- optional row context that helps preserve meaning when headers or labels live in adjacent cells on the same row.

Why this approach:
- Row-level summaries preserve spreadsheet semantics better than isolated cells because labels and values often only make sense together.
- Filtering at the contributing-cell level avoids paying embedding cost for rows that contain no textual signal.

Alternatives considered:
- Embedding the existing `row_context`/`column_context` for every cell and deduplicating later. Rejected because it still starts from per-cell embeddings and repeats nearly identical text.
- Embedding whole sheets. Rejected because it loses locality and makes search hits too coarse to act on.

### 3. Add XLSX row-embedding persistence keyed separately from cell `storage_id`

The current `item_embeddings` table is keyed one-to-one by `items.storage_id`, which is no longer sufficient for XLSX row embeddings because one vector must map to multiple cells. The store layer should add a dedicated row-vector persistence model for XLSX, for example:
- a row embedding table keyed by a synthetic row embedding id;
- a mapping table that links each row embedding id to one or more cell `storage_id` values plus enough ordering or priority metadata to resolve hits predictably.

The stored row record should also retain sheet name and row number so searches can render useful metadata without reparsing the embedding text blob.

Why this approach:
- It preserves the existing embedding model for DOCX and PPTX instead of forcing all file types into a more complex many-to-many layout.
- It makes row-to-cell resolution explicit and queryable rather than encoding it inside opaque JSON blobs.

Alternatives considered:
- Overloading `item_embeddings.storage_id` with synthetic row ids. Rejected because the current foreign-key relationship points to `items`, and synthetic ids would break that invariant.
- Storing the row-to-cell mapping only inside embedding metadata JSON. Rejected because search resolution would become harder to query, validate, and migrate.

### 4. Resolve semantic and hybrid XLSX hits by mapping a row hit back to the most actionable contributing cell(s)

Semantic search for XLSX should rank row embeddings, then expand each winning row hit through the row-to-cell mapping. The primary hit returned to callers should still be an existing cell item so current `SearchHit` consumers keep working with document path, item id, locator, and preview. The selected representative cell should be chosen deterministically from the contributing cells, preferring the most text-bearing cell or, when needed, the first contributing cell in row order.

To preserve observability, the hit metadata should also include row-level provenance such as:
- matched sheet and row;
- contributing cell coordinates;
- whether the surfaced cell is a representative cell rather than a one-to-one semantic match.

Hybrid search should continue to union keyword and semantic candidates, but for XLSX the semantic half now contributes row-derived candidates that are normalized back to cell identities before merging.

Why this approach:
- It keeps the public search contract centered on actionable cell locations.
- It allows hybrid merging to continue using cell-level identities even though semantic retrieval is row-based.

Alternatives considered:
- Returning row-only search hits for semantic XLSX queries. Rejected because the rest of the product is built around concrete cell locators.
- Expanding every row hit into all contributing cells before ranking. Rejected because it would duplicate results heavily and distort hybrid scoring.

### 5. Keep XLSX keyword indexing unchanged and make row embedding generation a file-type-specific branch in the service layer

`items` and `items_fts` should continue to receive the same per-cell XLSX records they receive today. The optimization belongs only in the embedding generation path. `AppServices.index_document()` should therefore branch on `file_type == "xlsx"` when building embedding payloads and persistence records:
- DOCX and PPTX stay on the current one-item-to-one-embedding flow.
- XLSX uses the grouped row representation and writes row embeddings plus row-to-cell mappings.

Why this approach:
- It minimizes regression risk and keeps the change easy to reason about: keyword and editing paths remain stable, vector behavior changes only where needed.
- It avoids forcing non-XLSX file types through abstractions they do not need.

Alternatives considered:
- Generalizing all file types to a new “embedding unit” abstraction immediately. Rejected because the problem is currently XLSX-specific and a broader abstraction would add complexity without clear benefit.

## Risks / Trade-offs

- `[Representative-cell resolution may surface a different cell than a user expects]` -> Include row provenance in hit metadata and choose the surfaced cell deterministically from the contributing text-bearing cells.
- `[Aggressive text-like filtering could drop semantically important short labels or mixed-format values]` -> Keep the filter heuristic conservative, cover edge cases with XLSX-focused tests, and prefer inclusion when ambiguity is high.
- `[A new row-vector schema adds migration and query complexity]` -> Isolate it to XLSX-specific tables or code paths and leave the existing per-item embedding schema untouched for other file types.
- `[Rows with large amounts of text may create long embedding payloads]` -> Truncate or normalize row summaries predictably, preserving the highest-signal cells first.
- `[Hybrid ranking may behave differently because semantic candidates collapse multiple cells into one row candidate]` -> Normalize semantic candidates back to one representative cell before final merge and add regression tests around duplicate suppression and tie-breaking.

## Migration Plan

1. Add store support for XLSX row embeddings and row-to-cell mappings, plus any required schema migration/version bump.
2. Implement XLSX row grouping and text-like cell filtering in the adapter or an adjacent XLSX-specific indexing helper.
3. Update `AppServices.index_document()` to build and persist row embeddings for XLSX while leaving per-cell item indexing unchanged.
4. Update semantic and hybrid XLSX search paths to read row embeddings, map winning rows back to representative cells, and expose row provenance in hit metadata.
5. Add tests covering:
   - numeric-heavy sheets producing far fewer embeddings than cells;
   - rows with mixed text and numeric cells;
   - semantic hit resolution back to real cell ids;
   - hybrid deduplication between keyword cell hits and semantic row hits.

Rollback:

- Keyword indexing and editable cell behavior remain unchanged, so functional rollback is mostly about disabling the XLSX row-vector path.
- If the new vector tables need to be abandoned during development, they can be dropped without affecting canonical document and item records.

## Open Questions

- What exact heuristic should classify a cell as “text-like” for semantic purposes: strict numeric parsing, data-type checks from `openpyxl`, or a layered rule set combining both?
- When a row contains multiple meaningful text cells, should the representative hit cell prefer the first textual cell, the highest-information cell, or a header/value pairing strategy?
- Should semantic hit metadata expose all contributing cell coordinates by default, or should detailed row provenance remain internal unless a verbose/debug surface requests it?
