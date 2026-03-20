## 1. Embedding Foundation And Configuration

- [ ] 1.1 Add the `fastembed` dependency and create `src/offagent/adapters/embedding_provider.py` with the provider protocol and local implementation
- [ ] 1.2 Extend `src/offagent/config.py` and config loading with embedding model, embedding dimensions, vector candidate pool, and hybrid weight settings plus matching environment variables
- [ ] 1.3 Add focused configuration tests covering defaults, file loading, and environment override behavior for the new vector-search settings

## 2. Store Schema And Atomic Indexing

- [ ] 2.1 Extend `src/offagent/indexing/store.py` schema initialization and migration logic with `item_embeddings` and `embedding_meta`
- [ ] 2.2 Refactor store write helpers so document indexing can replace items, FTS rows, and embeddings in one transaction without helper-level commits
- [ ] 2.3 Add embedding metadata validation and sidecar upsert helpers keyed by `storage_id`
- [ ] 2.4 Extend indexing integration tests to cover keyword-only indexing compatibility and `with_embeddings=True` persistence for embedded documents

## 3. Adapter And Service Retrieval Logic

- [ ] 3.1 Extend DOCX, PPTX, and XLSX adapters with `build_embedding_text(...)`, including persisted XLSX row and column context needed for contextual embedding text
- [ ] 3.2 Update shared domain models and service entrypoints to support `with_embeddings`, `SearchMode`, `match_mode`, and per-source score metadata
- [ ] 3.3 Implement semantic retrieval over stored embeddings and the missing-embeddings behavior in `AppServices.search_corpus`
- [ ] 3.4 Implement deterministic hybrid candidate merge and weighted ranking with unit tests for cosine similarity and merge scoring

## 4. CLI And MCP Surface Updates

- [ ] 4.1 Extend `office-agent index` and `office-agent reindex` with `--with-embeddings` and `office-agent search` with `--mode`
- [ ] 4.2 Update CLI renderers and JSON output so search hits expose `match_mode` and `scores`, and map invalid mode or no-embeddings cases to the documented exit codes
- [ ] 4.3 Extend MCP request and response schemas plus `search_documents` to accept `mode` and return mode-aware search hit metadata
- [ ] 4.4 Add CLI and MCP tests covering semantic mode, hybrid mode, invalid mode rejection, and structured output parity

## 5. Diagnostics, Logging, And End-To-End Verification

- [ ] 5.1 Extend `office-agent doctor` to check embedding-provider importability, model loadability, and embedding-store consistency
- [ ] 5.2 Add INFO-level logging for embedding generation, semantic search execution, and hybrid merge completion
- [ ] 5.3 Add adapter, service, and transport-level tests for contextual XLSX embedding text, provider contract behavior, and search result transport schemas
- [ ] 5.4 Run the relevant automated tests and confirm the vector-search change meets the proposal, design, and spec requirements end to end
