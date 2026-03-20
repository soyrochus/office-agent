## Context

Office Agent currently indexes document items into SQLite and serves keyword search from the `items_fts` table through `AppServices.search_corpus`. Search results, CLI output, and MCP transport models all assume a single keyword score, while indexing persists only document and item rows. The proposed vector-search feature touches the adapter layer, shared services, SQLite schema, domain models, CLI rendering, MCP schemas, configuration loading, and doctor checks, so it needs an explicit design before implementation.

The current seams are workable but expose two constraints that matter for this change:

- `store.replace_document_items()` commits internally, which prevents a single atomic index transaction once embeddings are added.
- XLSX extraction currently stores only display-oriented cell metadata, so semantic retrieval needs a defined place to build richer embedding text without changing the canonical editable item identity.

## Goals / Non-Goals

**Goals:**

- Add semantic and hybrid retrieval without changing the current `DocumentRef` and `ItemRef` identity model.
- Keep `keyword` as the default search mode while extending the shared service layer, CLI, and MCP surfaces to support `semantic` and `hybrid`.
- Persist embeddings inside the existing SQLite index so deployment stays local-first and migration remains incremental.
- Make embedding generation part of a complete indexing transaction when `with_embeddings=True`, so item rows and embedding rows cannot drift after a successful run.
- Define deterministic hybrid scoring that can merge FTS and vector candidates into one ordered result list.

**Non-Goals:**

- Introducing approximate nearest-neighbor infrastructure such as FAISS, HNSW, or `sqlite-vec`.
- Changing the editable unit away from the existing indexed item identified by `item_id` and `storage_id`.
- Making semantic or hybrid search the default mode in this feature.
- Adding cloud embedding providers, GPU inference, or automatic re-embedding after configuration/model changes.

## Decisions

### 1. Add an embedding-provider abstraction backed by `fastembed`

Create `src/offagent/adapters/embedding_provider.py` with an `EmbeddingProvider` protocol and a `LocalEmbeddingProvider` implementation. `LocalEmbeddingProvider` will own the embedding model name and discovered dimensionality and will return packed `float32` blobs.

Rationale:

- The service layer should depend on a narrow protocol instead of directly importing the embedding library.
- `fastembed` keeps the feature local-first, avoids PyTorch-scale runtime weight, and already emits normalized vectors, which simplifies cosine search.

Alternatives considered:

- Calling `fastembed` directly from `AppServices`: rejected because it couples service logic to one provider and makes testing harder.
- Cloud embedding APIs: rejected because they introduce network dependency, credentials, and a different product contract than the rest of Office Agent.

### 2. Store embeddings as SQLite sidecar tables keyed by existing `storage_id`

Extend `store.initialize_schema()` with `item_embeddings` and `embedding_meta`. `item_embeddings.storage_id` remains a one-to-one mapping to `items.storage_id`, so every semantic hit resolves to an already indexed editable item. `embedding_meta` stores the active model regime and is validated before embedding writes.

Rationale:

- Preserves the current identity model and avoids inventing a second search-only identifier.
- Keeps backups, migrations, and diagnostics in one database file.
- Makes hybrid search a join over the existing indexed corpus rather than a separate subsystem.

Alternatives considered:

- Separate vector database: rejected because it complicates operations and weakens the single-source-of-truth model.
- Storing embeddings inline on `items`: rejected because it mixes large binary payloads into the main item table and makes schema evolution less clear.

### 3. Refactor indexing writes to be atomic at the document level

`AppServices.index_document()` will become the transaction boundary for document indexing. The store layer should expose write helpers that do not commit independently, or a single composite helper that replaces item rows and embeddings together. The final commit occurs only after document metadata, item rows, FTS rows, embedding metadata validation, and optional embedding upserts all succeed.

When `with_embeddings=False`, indexing keeps the current keyword-only behavior and leaves embedding rows untouched unless the document content is being reindexed with embeddings enabled. When `with_embeddings=True`, any previous embeddings for the document are replaced in the same transaction as the fresh item rows.

Rationale:

- The feature explicitly requires no partial embedding state after a complete index run.
- The current internal commit in `replace_document_items()` would otherwise allow items to update while embeddings fail partway through generation or storage.

Alternatives considered:

- Best-effort embedding writes after item commit: rejected because it creates inconsistent index state that is hard to reason about and diagnose.
- Wrapping current helpers in nested transactions: rejected because the helpers already commit, so the service cannot guarantee atomicity without refactoring.

### 4. Build contextual embedding text in adapters, with XLSX enriched from extraction metadata

Add `build_embedding_text(item: IndexedItem, document_path: Path) -> str` to each document adapter module. DOCX and PPTX return `item.content_text` unchanged. XLSX returns a structured block containing workbook name, sheet name, cell coordinate, row context, column context, and cell value.

To avoid reopening workbooks per cell during embedding generation, XLSX extraction should persist the additional row and column context needed to build that block in `IndexedItem.metadata`. `build_embedding_text()` then becomes a pure formatter over the indexed item plus document path.

Rationale:

- Keeps format-specific embedding text rules next to the extraction logic that understands the source document.
- Avoids making the service layer parse XLSX semantics.
- Prevents an O(items) workbook reopen cost during embedding generation.

Alternatives considered:

- Generating all embedding text in `AppServices`: rejected because it forces format-specific branching into the service layer.
- Reopening the workbook for every XLSX item during embedding generation: rejected for avoidable performance cost and implementation complexity.

### 5. Add explicit search modes and mode-aware result fields in the shared domain model

Extend `SearchHit` with `match_mode` and `scores`, while keeping the existing `score` field for backward-compatible ordering and display. Add `SearchMode = Literal["keyword", "semantic", "hybrid"]` at the service boundary and propagate it through CLI and MCP inputs.

- `keyword`: existing FTS path, with `match_mode="keyword"` and `scores` omitted or set consistently to keyword-only values.
- `semantic`: embed the query, scan stored embedding blobs in Python, compute cosine similarity by dot product, and return hits with `match_mode="semantic"`.
- `hybrid`: run both retrieval paths, union by `storage_id`, and emit a merged hit with both component scores and the final score.

Rationale:

- Search mode is part of the product contract, not just an internal implementation detail.
- The new fields let CLI JSON and MCP responses preserve enough provenance for testing and downstream consumers.

Alternatives considered:

- Separate result types per mode: rejected because it would fragment the interfaces and complicate renderers and schemas.
- Returning only a final merged score in hybrid mode: rejected because the feature explicitly needs per-source score visibility.

### 6. Use deterministic hybrid scoring based on normalized per-source ranks

Hybrid retrieval should not directly combine raw FTS `bm25` values with cosine similarity because those score ranges are not comparable. Instead:

- collect up to `vector_search_top_k` candidates from each retrieval path;
- rank candidates within each source;
- convert rank to a normalized source score, using a monotonic reciprocal-rank style formula;
- compute `final = hybrid_keyword_weight * keyword_score + hybrid_semantic_weight * semantic_score`;
- sort by `final`, then by semantic score, keyword score, document path, and item id for deterministic ties.

Raw semantic similarity can still be retained for diagnostics if needed, but the hybrid merge contract should use normalized source scores.

Rationale:

- Stable across corpora and insensitive to FTS score scale quirks.
- Easy to explain, test, and reproduce in unit tests.

Alternatives considered:

- Min-max normalization over raw scores: rejected because it is unstable for small candidate sets and still depends on incompatible raw score distributions.
- Semantic-only reranking of keyword results: rejected because the feature requires unioned hybrid retrieval, not just reranking exact keyword matches.

### 7. Keep configuration and doctor checks aligned with the persisted embedding regime

Add config fields and env vars for model name, dimensions, vector candidate pool, and hybrid weights. Doctor checks should validate:

- the embedding provider import path;
- model loadability for the configured model;
- index path readiness including the new tables;
- metadata consistency between config and `embedding_meta` when embeddings already exist.

Rationale:

- Embedding configuration is operationally meaningful and must be visible in the same place as the rest of runtime config.
- Doctor is the existing place for surfacing dependency and index readiness failures before users hit them in indexing or search flows.

Alternatives considered:

- Silent metadata overwrite on model changes: rejected because it would make stored embeddings semantically invalid without an explicit reindex.

## Risks / Trade-offs

- [First-run model download adds latency and possible offline failure] -> Surface it clearly in doctor and indexing logs; do not hide provider/model load failures.
- [Python-side cosine search scans all stored embeddings for the candidate set] -> Limit scope to the expected corpus size, cap semantic/hybrid candidate pools via config, and keep ANN solutions out of this feature.
- [Refactoring store commits can regress existing indexing behavior] -> Add integration tests around keyword-only index/reindex paths before and after embedding-enabled indexing.
- [XLSX contextual metadata can increase item payload size] -> Store only the row/column context needed for embedding text and keep `preview`/editable semantics unchanged.
- [Hybrid scoring may surprise users if weights are poorly chosen] -> Provide explicit config defaults and include per-source scores in outputs so ranking remains inspectable.

## Migration Plan

1. Add schema migration for `item_embeddings` and `embedding_meta` in `store.initialize_schema()`.
2. Refactor store write helpers so document indexing can commit once per document.
3. Add embedding provider, config values, and doctor checks.
4. Extend adapters and domain models to support embedding text and mode-aware search hits.
5. Implement semantic and hybrid search in `AppServices`, then wire CLI and MCP inputs/outputs.
6. Add unit, integration, CLI, and MCP coverage for keyword compatibility, embedding indexing, semantic search, hybrid search, and invalid mode handling.

Rollback:

- Code rollback is straightforward because keyword search remains the default path.
- Existing databases can safely retain the new tables; older code can ignore them if schema compatibility permits. If cleanup is required during development, dropping the sidecar tables is sufficient because they do not replace canonical item data.

## Open Questions

- Should `SearchHit.score` remain the raw source score in keyword/semantic modes and the final merged score in hybrid mode, or should it always expose the ordering score while `scores` carries raw detail? The implementation should settle this before transport tests are written.
- How should the service surface the “semantic search requested but no embeddings are indexed” case internally so the CLI can exit with code 3 without treating it as a generic error?
- Should hybrid weights be validated to sum to `1.0`, or should the implementation normalize arbitrary positive weights at load time?
