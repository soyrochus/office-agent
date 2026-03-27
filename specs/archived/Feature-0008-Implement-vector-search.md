# Feature 0009 — Vector Search (Semantic & Hybrid Retrieval)

## Goal

Extend the existing FTS5-based search with a sidecar vector index over the same indexed items, enabling semantic and hybrid retrieval without disturbing the existing locate-and-patch product contract. The canonical editable unit remains the `ItemRef` identified by a stable `item_id`. Every search hit — regardless of mode — resolves to an existing indexed item.

---

## Scope

### Included

#### Embedding provider layer

- New `EmbeddingProvider` protocol in `src/offagent/adapters/embedding_provider.py`
- One concrete implementation: `LocalEmbeddingProvider`, backed by [`fastembed`](https://github.com/qdrant/fastembed) — a pure Python + `onnxruntime` library with no PyTorch or TensorFlow dependency (~80 MB runtime footprint vs ~600 MB for PyTorch)
- Default model: `BAAI/bge-small-en-v1.5` (33 MB, 384 dimensions, downloaded once and cached in `~/.cache/fastembed` on first use)
- Provider is responsible for: model name, dimensionality, and batch text → `float32` bytes conversion
- `fastembed` outputs L2-normalised (unit-length) vectors; the stored BLOBs are therefore already unit-length and cosine similarity reduces to a dot product at query time

#### Sidecar vector storage

- Two new tables added to the existing SQLite database by `store.py` schema migration:
  - `item_embeddings` — one `float32` BLOB per indexed item, keyed by `storage_id`
  - `embedding_meta` — key/value registry for the active embedding regime

#### Contextual embedding text for XLSX

- For XLSX cells, the text submitted to the embedding provider is a structured context block (workbook name, sheet name, cell coordinate, row context, column context, value), not the raw cell value
- Adapters expose a `build_embedding_text(item: IndexedItem, document_path: Path) -> str` helper for this enrichment; DOCX and PPTX adapters return `item.content_text` unchanged

#### Embedding indexing integrated into the existing index path

- `AppServices.index_document` gains an optional `with_embeddings: bool = False` parameter
- When `with_embeddings=True`: after FTS items are written, build embedding texts, call the provider in batch, and upsert the resulting BLOBs into `item_embeddings`
- `AppServices.index_path` and `AppServices.reindex_path` gain the same optional parameter and propagate it through to `index_document`
- Stale embedding detection: when a document's `content_hash` changes, embeddings are regenerated in the same pass; no partial-embedding state is possible after a complete index run

#### Search modes

- `AppServices.search_corpus` gains a `mode: SearchMode = "keyword"` parameter
- `SearchMode = Literal["keyword", "semantic", "hybrid"]`
- `keyword` — existing FTS5 path only; behaviour unchanged
- `semantic` — embed the query, search `item_embeddings` by cosine similarity (computed in Python over the BLOB column; no SQLite extension required), return hits as `SearchHit` objects with `match_mode="semantic"`
- `hybrid` — run both paths (top `limit` from each), union by `storage_id`, score with a deterministic weighted formula, return merged `SearchHit` list with `match_mode="hybrid"` and per-source scores

#### Extended `SearchHit` domain model

`SearchHit` gains three optional fields (all `None` for `keyword`-only results):

```
match_mode : "keyword" | "semantic" | "hybrid" | None
scores     : dict[str, float] | None   # keys: "keyword", "semantic", "final"
```

Existing fields and their semantics are unchanged.

#### CLI changes

- `office-agent index <path> [--with-embeddings]` — pass `with_embeddings=True` to the service
- `office-agent reindex <path> [--with-embeddings]` — same
- `office-agent search <query> [--mode keyword|semantic|hybrid]` — default is `keyword`
- The `--mode` flag accepts the three literal values only; any other value exits with code 2
- Human-readable output includes `match_mode` and `scores` when present
- `--json` output includes the new fields in every hit object

#### MCP changes

- `search_documents` tool gains an optional `mode` parameter (`"keyword"` | `"semantic"` | `"hybrid"`, default `"keyword"`)
- All other MCP tools are unchanged

#### Configuration additions

Two new optional keys in `office-agent.toml` (under `[offagent]`):

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `embedding_model` | str | `"BAAI/bge-small-en-v1.5"` | `fastembed`-compatible model name |
| `embedding_dimensions` | int | `384` | Vector dimensions (must match model) |
| `vector_search_top_k` | int | `20` | Candidate pool per retrieval path in hybrid/semantic mode |
| `hybrid_keyword_weight` | float | `0.4` | Weight for keyword score in hybrid merge |
| `hybrid_semantic_weight` | float | `0.6` | Weight for semantic score in hybrid merge |

Corresponding env vars: `OFFAGENT_EMBEDDING_MODEL`, `OFFAGENT_EMBEDDING_DIMENSIONS`, `OFFAGENT_VECTOR_SEARCH_TOP_K`, `OFFAGENT_HYBRID_KEYWORD_WEIGHT`, `OFFAGENT_HYBRID_SEMANTIC_WEIGHT`.

#### Doctor command additions

- Check that the embedding provider module can be imported
- Check that the configured embedding model can be loaded
- Check that `item_embeddings` table exists and is consistent with `embedding_meta`

#### Observability additions

Log the following at INFO level:

- Embedding generation started (document path, item count)
- Embedding generation completed (document path, item count, duration)
- Semantic search executed (query, top-k, hit count)
- Hybrid merge completed (keyword hits, semantic hits, merged hits)

#### Testing additions

- Unit tests: `EmbeddingProvider` protocol contract, contextual embedding text builder for XLSX, cosine similarity helper, hybrid merge logic, score formula
- Adapter tests: `build_embedding_text` for each format against fixture corpus items
- Integration tests for `index_document(with_embeddings=True)`: verify `item_embeddings` rows exist and dimensions match config
- CLI tests:
  - `office-agent index ./tests/fixtures --with-embeddings` exits 0
  - `office-agent search "query" --mode semantic` returns hits with `match_mode="semantic"` in `--json` output
  - `office-agent search "query" --mode hybrid` returns hits with `scores` present in `--json` output
  - `office-agent search "query" --mode invalid` exits 2
  - Search with `--mode semantic` when no embeddings are indexed exits 3 (no results, not an error)
- MCP integration test: `search_documents` with `mode="hybrid"` returns valid result structure

### Excluded

- GPU inference or cloud embedding APIs
- Approximate nearest-neighbour indexing (sqlite-vec, faiss, hnswlib) — cosine similarity over in-memory BLOBs is sufficient for the expected corpus size
- Learning-to-rank or ML-based re-ranking
- Automatic migration of hybrid to default mode — `keyword` remains the default throughout this feature
- Batch re-embedding command (`reembed`) — model changes require a full `reindex --with-embeddings`
- Embedding of DOCX table cells, headers, footers, PPTX notes, or XLSX formula semantics

---

## Module Structure Changes

```
src/offagent/
├── adapters/
│   ├── embedding_provider.py    # NEW — EmbeddingProvider Protocol + local implementation
│   ├── docx_adapter.py          # MODIFIED — build_embedding_text (passthrough)
│   ├── pptx_adapter.py          # MODIFIED — build_embedding_text (passthrough)
│   └── xlsx_adapter.py          # MODIFIED — build_embedding_text (contextual block)
├── app/
│   └── services.py              # MODIFIED — index_document + search_corpus
├── config.py                    # MODIFIED — new embedding config keys
├── domain/
│   └── models.py                # MODIFIED — SearchHit.match_mode + SearchHit.scores
├── indexing/
│   └── store.py                 # MODIFIED — item_embeddings + embedding_meta schema + vector ops
└── interfaces/
    ├── cli.py                   # MODIFIED — --with-embeddings, --mode
    └── mcp.py                   # MODIFIED — mode param on search_documents
```

---

## Storage Schema

### New table: `item_embeddings`

```sql
CREATE TABLE IF NOT EXISTS item_embeddings (
    storage_id  TEXT PRIMARY KEY REFERENCES items(storage_id),
    model_name  TEXT NOT NULL,
    dimensions  INTEGER NOT NULL,
    embedding   BLOB NOT NULL,
    updated_at  TEXT NOT NULL
);
```

`storage_id` is the same primary key used in the `items` table. This preserves the single-identity design: one embedding row per indexed item row, no new identity system.

### New table: `embedding_meta`

```sql
CREATE TABLE IF NOT EXISTS embedding_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

Populated keys: `model_name`, `dimensions`, `similarity_metric` (always `"cosine"` in this version), `schema_version` (always `"1"`). Written on first embedding index run; validated on every subsequent run. Mismatch between config and stored meta is a fatal error at indexing time (not silently overwritten).

### Schema migration

`store.initialize_schema` creates both tables if absent. Existing databases without them are upgraded in-place. The migration is idempotent.

---

## Embedding Provider Contract

```python
# src/offagent/adapters/embedding_provider.py

import struct
from typing import Protocol

from fastembed import TextEmbedding


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed_texts(self, texts: list[str]) -> list[bytes]:
        """Return one float32 BLOB per input text, length == dimensions * 4."""
        ...


class LocalEmbeddingProvider:
    """fastembed-backed provider. Vectors are L2-normalised by fastembed before packing."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)
        # Derive dimensions from a probe embedding rather than hardcoding
        probe = next(self._model.embed(["probe"]))
        self.dimensions = len(probe)

    def embed_texts(self, texts: list[str]) -> list[bytes]:
        return [
            struct.pack(f"{self.dimensions}f", *vec)
            for vec in self._model.embed(texts)
        ]
```

Output BLOBs are `dimensions * 4` bytes, little-endian `float32`. `fastembed` L2-normalises all vectors before returning them, so stored BLOBs are unit-length.

### Cosine similarity at query time

Because stored vectors are unit-length, cosine similarity is a dot product. No `numpy` or SQLite extension is required:

```python
# indexing/store.py helper

import struct

def _dot_product(a: bytes, b: bytes) -> float:
    n = len(a) // 4
    va = struct.unpack(f"{n}f", a)
    vb = struct.unpack(f"{n}f", b)
    return sum(x * y for x, y in zip(va, vb))
```

### Dependency addition

```toml
# pyproject.toml
fastembed = ">=0.3"
```

`fastembed` pulls in `onnxruntime` as its only non-trivial transitive dependency. No GPU packages, no PyTorch, no TensorFlow.

---

## XLSX Contextual Embedding Text

For an XLSX item, the string submitted to the embedding provider is:

```
Workbook: <display_name>
Sheet: <sheet_name>
Cell: <coordinate>
Row context: <values of other non-empty cells in the same row, comma-separated, truncated>
Column context: <values of other non-empty cells in the same column, up to 3, comma-separated, truncated>
Value: <cell_value>
```

Row/column context is derived from the already-extracted `IndexedItem` objects for the same document passed to the indexing call, not by re-opening the file at embedding time.

---

## Search Modes — Detailed Behaviour

### `keyword` (unchanged)

Delegates to existing `store.search_items`. Returns `SearchHit` with `match_mode=None`, `scores=None`.

### `semantic`

1. Embed the query text using the active `EmbeddingProvider`
2. Load all `item_embeddings` rows for the relevant document scope (or all, if no `--doc` filter) — this is acceptable for the expected corpus size
3. Compute cosine similarity between query vector and each stored vector
4. Return top `vector_search_top_k` hits, joined to `items` and `documents`
5. Set `match_mode="semantic"`, `scores={"keyword": None, "semantic": <sim>, "final": <sim>}`

### `hybrid`

1. Run `keyword` path → top `vector_search_top_k` hits with FTS5 scores, normalised to [0, 1]
2. Run `semantic` path → top `vector_search_top_k` hits with cosine scores
3. Union by `storage_id`
4. For items appearing in both: `final = keyword_weight * keyword_score + semantic_weight * semantic_score`
5. For items appearing in keyword only: `final = keyword_weight * keyword_score`
6. For items appearing in semantic only: `final = semantic_weight * semantic_score`
7. Sort descending by `final`, return top `limit` hits
8. Set `match_mode="hybrid"`, `scores={"keyword": <score or 0.0>, "semantic": <score or 0.0>, "final": <final>}`

Score normalisation for FTS5: divide raw FTS5 rank (a negative float) by the maximum absolute rank in the candidate set to map to [0, 1].

---

## Acceptance Criteria

- `office-agent index ./tests/fixtures --with-embeddings` exits 0 and populates `item_embeddings` rows for every indexed item
- `office-agent search "find the slide about cost reductions" --mode semantic` returns at least one hit when the fixture PPTX contains relevant content
- `office-agent search "EBITDA" --mode keyword` behaves identically to the pre-feature `search` command
- `office-agent search "revenue forecast" --mode hybrid --json` returns objects with `match_mode`, `scores.keyword`, `scores.semantic`, and `scores.final` fields
- `office-agent search "query" --mode invalid` exits 2
- `office-agent index ./tests/fixtures` (without `--with-embeddings`) does not write to `item_embeddings`; a subsequent `--mode semantic` search returns 0 hits cleanly (exit 0)
- After a document is replaced and reindexed with `--with-embeddings`, the old `item_embeddings` rows for that document are replaced with fresh embeddings
- `embedding_meta` mismatch (model or dimensions changed in config) raises a fatal error with a descriptive message before any embedding is generated
- MCP `search_documents` with `mode="hybrid"` returns the same structure as the CLI `--json` output
- All existing CLI and MCP tests continue to pass without modification
- `office-agent doctor` reports the embedding model as PASS when correctly configured

---

## Architectural Notes

This feature removes the explicit MVP exclusion of "Embeddings or vector search" from the architecture guidelines (§16). All other exclusions in §16 remain in effect.

The layered call direction is preserved: `interfaces → services → adapters/store`. The embedding provider sits alongside the existing document adapters and is called exclusively from the service layer during indexing and search. No adapter may call the embedding provider; no interface layer code may call the provider directly.

The existing `item_id` and `storage_id` identity system is the join key between FTS hits, vector hits, and patch operations. No new identity system is introduced.
