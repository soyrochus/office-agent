## 1. XLSX Row Embedding Preparation

- [x] 1.1 Add XLSX-specific grouping and filtering helpers that derive text-bearing row embedding inputs from extracted cell items without changing the existing cell-level `IndexedItem` output used for keyword search and editing
- [x] 1.2 Define the deterministic row embedding text format and representative-cell selection rules for grouped XLSX rows, including the row provenance that must be preserved for later hit resolution

## 2. Store Schema And Persistence

- [x] 2.1 Extend `src/offagent/indexing/store.py` schema initialization and migrations with dedicated XLSX row-embedding and row-to-cell mapping tables
- [x] 2.2 Add store helpers to replace, fetch, and delete XLSX row embeddings and their contributing cell mappings as one document refresh set while preserving the existing per-item embedding flow for DOCX and PPTX
- [x] 2.3 Extend store-level tests to cover schema bootstrap, document reindex replacement, and queryable row-to-cell mappings for XLSX embeddings

## 3. Indexing And Search Integration

- [x] 3.1 Update `AppServices.index_document()` so XLSX indexing with `with_embeddings=True` writes row embeddings plus row-to-cell mappings, while non-XLSX indexing keeps the current one-item-to-one-embedding behavior
- [x] 3.2 Update semantic search for XLSX to rank row embeddings and resolve each hit back to a deterministic contributing cell with row provenance metadata
- [x] 3.3 Update hybrid search for XLSX to merge keyword cell hits with row-derived semantic hits using the resolved cell identity and deterministic duplicate suppression

## 4. Verification

- [x] 4.1 Add adapter and service tests covering numeric-heavy rows, mixed text-and-numeric rows, representative-cell selection, and semantic hit metadata for XLSX row embeddings
- [x] 4.2 Add integration tests covering XLSX reindex replacement, missing-embeddings behavior, and hybrid search resolution against stored row embeddings
- [x] 4.3 Run the relevant automated tests and confirm the change satisfies the proposal, design, and spec requirements end to end
