## Why

Semantic indexing for XLSX currently does too much work for spreadsheet-shaped data because it embeds every populated cell, including many numeric-only cells that add cost without improving retrieval quality. This change reduces indexing cost by embedding only text-like XLSX content at a row granularity while preserving the cell-level location metadata needed to return actionable search hits.

## What Changes

- Change XLSX semantic indexing from one-embedding-per-cell to one-embedding-per-text-bearing-row.
- Filter XLSX semantic embedding inputs so numeric-only, empty, and otherwise non-text-like cells do not contribute to vector generation.
- Preserve explicit source-cell metadata for each row embedding so semantic and hybrid search can still resolve hits to real workbook locations.
- Keep the existing cell-level item index, locators, read/write flows, and keyword XLSX search behavior unchanged.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `vector-search`: Change XLSX embedding construction and semantic/hybrid hit resolution to use row-level embeddings backed by source-cell metadata instead of per-cell embeddings.
- `local-index-store`: Extend vector-side persistence so XLSX row embeddings retain a queryable mapping back to the contributing cell items and coordinates.

## Impact

- Affected code: `src/offagent/adapters/xlsx_adapter.py`, `src/offagent/app/services.py`, `src/offagent/indexing/store.py`
- Likely model/interface changes: semantic XLSX hit metadata and any supporting storage records for row-to-cell mapping
- Systems: XLSX indexing performance, vector search behaviour for spreadsheets, semantic/hybrid hit rendering
