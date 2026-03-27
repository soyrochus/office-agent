# Analysis implementation of Vector-search 

The current shape is already favourable for adding semantic retrieval. `office-agent` has a shared application core, a Typer CLI, an MCP server, and today it indexes DOCX paragraphs, PPTX text shapes, and XLSX cells into a local SQLite + FTS5 index, with stable item identifiers such as `para:<n>`, `slide:<n>:shape:<id>`, and `sheet:<name>!<coordinate>`. Search currently goes through the `search` command and accepts `query`, optional `--type`, and optional `--doc`. The project also already reindexes after writes and has stale-locator detection, which is exactly the kind of machinery you want to preserve when adding vectors. ([GitHub][1])

So I would not treat semantic search as a separate subsystem. I would treat it as a second retrieval path attached to the same indexed items.

The architectural rule should be: FTS5 remains the lexical index, vectors become a sidecar semantic index, and the canonical editable unit stays the existing item. That matters because your whole application depends on being able to go from a hit to an exact document location and then safely edit it. If semantic search returns anything other than existing indexed items, it will fight the design instead of extending it.

Given the current repo, the most natural fit is not a lone `--semantic-search` flag. A mode parameter is cleaner and scales better:

```bash
office-agent search "revenue forecast" --mode keyword
office-agent search "revenue forecast" --mode semantic
office-agent search "revenue forecast" --mode hybrid
```

That matches the current `search` command shape and avoids flag proliferation. Your present CLI already routes `search` through a shared `services.search_corpus(...)` call, so this is likely one service signature change rather than a CLI redesign. ([GitHub][2])

I would extend the storage model like this.

Keep the existing document and item tables exactly as they are for FTS. Add one embeddings table keyed by the same indexed item id or row id. Something structurally close to:

```sql
CREATE TABLE item_embeddings (
    item_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding BLOB NOT NULL,
    updated_at TEXT NOT NULL
);
```

If your existing internal schema uses integer row ids behind the scenes, use those instead. The point is one embedding per already indexed item. No second identity system.

Then add one metadata table for the embedding regime:

```sql
CREATE TABLE embedding_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

Store at least model name, dimension count, similarity metric, and embedding schema version there. That prevents silent corruption when you later swap models.

For indexing, the good news is that your granularity is already usable.

DOCX is paragraph-level. That is acceptable for v1 semantic retrieval, though later you may want heading-aware paragraph grouping for better recall on long documents. README confirms paragraph-level item ids are already stable and empty paragraphs are kept for numbering stability. ([GitHub][1])

PPTX is shape-level for text-bearing shapes. That is also acceptable, and probably better than slide-level because edits are shape-specific. README confirms only text-frame shapes are indexed and non-text shapes are excluded. ([GitHub][1])

XLSX is cell-level. That is the weak point. Cell-level semantic search is often poor because many cells have too little context. README confirms current indexing is at non-empty cell level, with formulas indexed by formula text. ([GitHub][1])

So for Excel I would not simply embed raw cell text. I would build a contextual embedding text for each indexed cell. For example:

```text
Workbook: finance.xlsx
Sheet: Budget2026
Cell: E17
Row context: Marketing Spain
Column context: Forecast Q3
Value: 125000
```

That preserves editability at cell level while making the embedding semantically meaningful. Without that, semantic search over spreadsheets will be disappointing.

For local embedding creation, keep it in Python during indexing. Do not push embedding generation into SQLite. Use one local CPU-friendly model. Then serialize the output as `float32` bytes and store in the `BLOB`. That aligns with how SQLite vector extensions expect vectors to be stored. The app is already local-first and Python-based, so adding a local embedding provider at the indexing layer is the least disruptive option. The project currently depends on Python 3.13, `python-docx`, `python-pptx`, `openpyxl`, `pydantic`, `python-dotenv`, and `typer`; there is no existing ML dependency, so this would be an explicit new layer rather than a tweak. ([GitHub][3])

Concretely, I would add an embedding adapter interface under the existing layered structure. The repo already has `adapters`, `app`, `domain`, `indexing`, `interfaces`, and `storage`, which is a good place to keep this clean. ([GitHub][4])

Something like:

```python
class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed_texts(self, texts: list[str]) -> list[bytes]:
        ...
```

Then one implementation, initially local only, for a small sentence-transformer or ONNX-backed model.

The indexing flow should become:

extract item text -> build embedding text -> write/update FTS item -> write/update vector blob

not:

extract item text -> create a separate semantic document index

That distinction keeps reindexing and stale-locator behaviour coherent. README states writes already create versioned outputs by default and trigger automatic reindexing. Semantic indexing should piggyback on that same reindex path. ([GitHub][1])

On search execution, I would implement three modes.

`keyword` runs the current FTS5 query only.

`semantic` embeds the query locally, searches the vector index, then returns the same item objects you already use.

`hybrid` does both, merges candidates, and scores them.

For the first version, do not attempt sophisticated learning-to-rank. Use a deterministic merge. For example:

* top 20 FTS hits
* top 20 vector hits
* union by item id
* combine scores with a simple weighted formula
* preserve match provenance in the result payload

This provenance matters. Users will trust a hit more if they can see whether it came from keyword, semantic, or both.

So a result object should grow fields like:

```json
{
  "item_id": "sheet:Budget2026!E17",
  "document_path": "/docs/finance.xlsx",
  "text": "125000",
  "match_mode": "hybrid",
  "scores": {
    "keyword": 0.21,
    "semantic": 0.84,
    "final": 0.61
  }
}
```

That also fits your current human-readable and JSON CLI output modes. README explicitly says those output modes are shared across commands, so this is an additive change, not a conceptual break. ([GitHub][1])

There is one assumption to challenge. You may be tempted to make semantic search global and automatic from the start. I would not. In Office tooling, exact lexical search is often still the best tool for codes, account numbers, legal clauses, formula fragments, and specific slide text. Semantic search is strongest for paraphrase and intent. Hybrid should probably become the default only after you validate it against real documents.

A pragmatic rollout would be:

First, add storage and indexing support for embeddings, but keep search defaulting to keyword.

Second, add `--mode semantic|hybrid`.

Third, once validated, make `hybrid` the default and keep `keyword` for exact behaviour.

I would also add a dedicated maintenance command. Right now you have `index`, `reindex`, and document operations. For vectors, one of these is needed:

```bash
office-agent embed-index /path/to/docs
office-agent reembed /path/to/doc.docx
office-agent search "..." --mode semantic
```

or, more elegantly, extend existing indexing:

```bash
office-agent index ./docs --with-embeddings
office-agent reindex ./docs/report.docx --with-embeddings
```

The second option fits the current CLI better because the repo already frames indexing as one concern and search as another. The only reason to separate embedding rebuilds is operational convenience when changing models.

At the MCP layer, no radical change is needed. README says the current MCP tools include `search_documents`, `locate_item`, `read_item`, and write operations, and that the MCP layer reuses the shared service layer rather than duplicating logic. That is good. Add an optional `mode` parameter to `search_documents` and keep everything else the same. ([GitHub][1])

The most important repo-specific recommendation is this:

Do not create semantic chunks that differ from your editable items unless you are prepared to introduce a mapping layer back to the existing item ids.

Because right now your product value is not retrieval alone. It is retrieval plus precise locate plus safe modification. The current identifiers and stale-locator discipline are part of the product, not an implementation detail. README makes that explicit. ([GitHub][1])

So my verdict is:

Yes, semantic search is a natural extension for `office-agent`.
It should be implemented as a sidecar vector index over the same indexed items.
The CLI should probably use `--mode keyword|semantic|hybrid`, not a one-off `--semantic-search`.
Excel needs contextualized cell embeddings, or it will underperform.
Reindexing should regenerate embeddings through the existing write and refresh paths, not through a disconnected pipeline.

A compact target shape for the CLI would be:

```bash
office-agent index ./docs --with-embeddings
office-agent reindex ./docs/q3-plan.pptx --with-embeddings
office-agent search "find the slide about cost reductions" --mode hybrid
office-agent search "EBITDA" --mode keyword
```

That fits the repo as it exists now, instead of forcing a new product shape onto it.

[1]: https://github.com/soyrochus/office-agent/blob/main/README.md "office-agent/README.md at main · soyrochus/office-agent · GitHub"
[2]: https://raw.githubusercontent.com/soyrochus/office-agent/main/src/offagent/interfaces/cli.py "raw.githubusercontent.com"
[3]: https://github.com/soyrochus/office-agent/blob/main/pyproject.toml "office-agent/pyproject.toml at main · soyrochus/office-agent · GitHub"
[4]: https://github.com/soyrochus/office-agent/tree/main/src/offagent "office-agent/src/offagent at main · soyrochus/office-agent · GitHub"
