## Why

Keyword-only FTS search is adequate for exact phrasing, but it misses semantically related content and makes cross-format retrieval brittle when wording differs. This change adds semantic and hybrid retrieval on top of the existing indexed item model so Office Agent can find the right editable item without changing its locate-and-patch contract.

## What Changes

- Add vector-search support over existing indexed items using a local embedding provider and a sidecar embedding store keyed by the current item identity.
- Add `keyword`, `semantic`, and `hybrid` search modes to the shared search flow while keeping `keyword` as the default behavior.
- Extend indexing so documents can optionally generate embeddings during index and reindex operations, including contextual embedding text for XLSX cells.
- Extend CLI and MCP search surfaces to accept a search mode and return mode-aware match metadata and scores.
- Extend configuration and diagnostics to cover embedding model settings, vector-search tuning, and embedding-store readiness checks.

## Capabilities

### New Capabilities
- `vector-search`: Semantic and hybrid retrieval over indexed Office document items, including embedding generation, cosine similarity search, hybrid scoring, and mode-aware search results.

### Modified Capabilities
- `local-index-store`: Persist embedding vectors and embedding metadata alongside the existing SQLite document and item index.
- `config-and-diagnostics`: Add embedding and hybrid-search configuration plus doctor checks for embedding provider availability, model loading, and vector-store consistency.
- `cli-output-modes`: Ensure search output includes match-mode and scoring metadata in both human-readable and `--json` responses when vector modes are used.
- `mcp-service-tools`: Extend `search_documents` to accept retrieval mode selection and return the same structured mode-aware search results as the shared service layer.

## Impact

- Affected code spans `src/offagent/adapters/`, `src/offagent/app/services.py`, `src/offagent/config.py`, `src/offagent/domain/models.py`, `src/offagent/indexing/store.py`, `src/offagent/interfaces/cli.py`, and `src/offagent/interfaces/mcp.py`.
- Adds a local embedding dependency footprint via `fastembed` and its runtime model cache.
- Expands the SQLite schema with embedding sidecar tables and adds new indexing, search, CLI, MCP, diagnostics, and test coverage requirements.
