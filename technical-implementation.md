# Office-Agent: Technical Implementation

This document describes the complete technical architecture and implementation of **office-agent** (`offagent`), a local-first Office document automation platform. It follows the full OpenSpec specification corpus as defined in `/openspec/specs/` and the completed changes in `/openspec/changes/`.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Layers](#2-architecture-layers)
3. [Configuration and Diagnostics](#3-configuration-and-diagnostics)
4. [Security: Path Policy Guards](#4-security-path-policy-guards)
5. [Domain Models and Locators](#5-domain-models-and-locators)
6. [Local Index Store](#6-local-index-store)
7. [Format Adapters](#7-format-adapters)
   - 7.1 [DOCX Adapter](#71-docx-adapter)
   - 7.2 [PPTX Adapter](#72-pptx-adapter)
   - 7.3 [XLSX Adapter](#73-xlsx-adapter)
8. [Vector Search and Embeddings](#8-vector-search-and-embeddings)
9. [Write Semantics](#9-write-semantics)
   - 9.1 [Versioned Write Outputs](#91-versioned-write-outputs)
   - 9.2 [Stale-Locator Detection](#92-stale-locator-detection)
   - 9.3 [Write-Reindex Synchronization](#93-write-reindex-synchronization)
10. [Application Services Layer](#10-application-services-layer)
11. [MCP Interface](#11-mcp-interface)
    - 11.1 [Tool Surface (11 tools)](#111-tool-surface-11-tools)
    - 11.2 [MCP Models and Converters](#112-mcp-models-and-converters)
    - 11.3 [Error Mapping](#113-error-mapping)
    - 11.4 [Universal Locator Address Space](#114-universal-locator-address-space)
12. [CLI Interface](#12-cli-interface)
    - 12.1 [Commands](#121-commands)
    - 12.2 [Output Modes](#122-output-modes)
    - 12.3 [Exit Codes](#123-exit-codes)
13. [Indexing Progress Reporting](#13-indexing-progress-reporting)
14. [Document Structure Tools](#14-document-structure-tools)
15. [Test Coverage](#15-test-coverage)
    - 15.1 [Golden Fixture Corpus](#151-golden-fixture-corpus)
    - 15.2 [Acceptance Test Coverage](#152-acceptance-test-coverage)
16. [Data Flow Walkthrough](#16-data-flow-walkthrough)
17. [Error Hierarchy](#17-error-hierarchy)

---

## 1. System Overview

`offagent` enables AI agents and human operators to discover, inspect, and edit Office documents (`.docx`, `.pptx`, `.xlsx`) using a combination of full-text search, optional semantic (vector) search, and item-level read/write operations. The system is:

- **Local-first**: All state is stored in a local SQLite database. No remote service is required.
- **MCP-ready**: Exposes an 11-tool Model Context Protocol server over stdio so any MCP client (including Claude) can drive document operations.
- **CLI-driven**: Provides the same capabilities through a Typer-based command-line interface.
- **Non-destructive**: Writes produce versioned output files by default and never delete source documents, execute macros, or dereference external links.

The system is built and evolved through OpenSpec, which tracks requirements, specifications, and acceptance scenarios for each feature set. All active specifications live in `/openspec/specs/` and completed feature changes are archived in `/openspec/changes/archive/`.

---

## 2. Architecture Layers

The codebase is organized into six distinct layers, each with a single responsibility:

```
┌─────────────────────────────────────────────┐
│            Interfaces                        │
│   CLI (Typer)          MCP (FastMCP/stdio)   │
├─────────────────────────────────────────────┤
│          Application Services               │
│            app/services.py                  │
├──────────────┬──────────────────────────────┤
│   Indexing   │    Adapters (Format I/O)      │
│  store.py    │  docx / pptx / xlsx adapters │
├──────────────┴──────────────────────────────┤
│         Domain Models & Locators            │
│      domain/models.py  domain/locators.py   │
├─────────────────────────────────────────────┤
│     Infrastructure                          │
│  config.py  errors.py  path_policy.py       │
│  storage/versioning.py  embedding_provider  │
└─────────────────────────────────────────────┘
```

**Package layout** (`src/offagent/`):

| Path | Purpose |
|---|---|
| `config.py` | TOML + env-var configuration with cascading precedence |
| `errors.py` | Unified exception hierarchy |
| `path_policy.py` | allowed-root and output-root security enforcement |
| `domain/models.py` | Core domain objects (DocumentRef, ItemRef, SearchHit, …) |
| `domain/locators.py` | Locator parsing and resolution |
| `adapters/docx_adapter.py` | DOCX extraction and editing via python-docx |
| `adapters/pptx_adapter.py` | PPTX extraction and editing via python-pptx |
| `adapters/xlsx_adapter.py` | XLSX extraction and editing via openpyxl |
| `adapters/embedding_provider.py` | Optional vector embeddings via FastEmbed |
| `indexing/store.py` | SQLite schema, FTS5, embedding sidecars, CRUD |
| `app/services.py` | Business logic orchestration (shared by CLI and MCP) |
| `app/progress.py` | Progress reporting abstraction |
| `storage/versioning.py` | Versioned output path generation |
| `interfaces/cli.py` | Typer CLI entry point |
| `interfaces/cli_output.py` | Human-readable and JSON output formatting |
| `interfaces/cli_progress.py` | Terminal progress rendering |
| `interfaces/mcp.py` | FastMCP server builder and tool handlers |
| `interfaces/mcp_models.py` | Pydantic request/response transport models |
| `interfaces/mcp_converters.py` | Domain → MCP model adapters |

---

## 3. Configuration and Diagnostics

**Spec**: `openspec/specs/config-and-diagnostics/`

Configuration follows a cascading precedence model:

```
Built-in defaults → TOML file → Environment variables
```

The TOML config file path is resolved in order: `$OFFAGENT_CONFIG`, `./offagent.toml`, `~/.config/offagent/config.toml`. All settings can be overridden by environment variables prefixed `OFFAGENT_`.

Key settings:

| Setting | Type | Description |
|---|---|---|
| `index_path` | path | SQLite database file location |
| `document_roots` | list[path] | Directories scanned when indexing without explicit paths |
| `allowed_roots` | list[path] | Read-operation whitelist (policy enforcement) |
| `output_roots` | list[path] | Write-operation whitelist (policy enforcement) |
| `allow_inplace_overwrite` | bool | Enables in-place write mode (default: `false`) |
| `embedding.model` | str | FastEmbed model name (default: `BAAI/bge-small-en-v1.5`) |
| `embedding.dimensions` | int | Vector dimension (default: `384`) |
| `embedding.keyword_weight` | float | Hybrid search keyword weight |
| `embedding.semantic_weight` | float | Hybrid search semantic weight |

**Doctor command** (`offagent doctor`) performs health checks:
- Config file found and parseable
- `index_path` directory writable
- SQLite schema version matches current codebase
- Embedding model loadable (when embeddings enabled)
- All `document_roots` are accessible directories

---

## 4. Security: Path Policy Guards

**Spec**: `openspec/specs/security-path-guards/`

All file access is mediated through `path_policy.py`, which enforces two independent root lists.

### Allowed Roots Policy

Read operations (index, show, locate, read, search) require the resolved absolute path of every accessed file to be inside at least one configured `allowed_root`. Resolution:

1. Canonicalize the input path (`os.path.realpath`) to resolve symlinks and `..` traversal.
2. Check that the canonical path starts with at least one canonical `allowed_root`.
3. If no match: raise `PolicyRefusedError` (exit code 5 in CLI, `ToolError` in MCP).

### Output Roots Policy

Write operations (replace, append, write-cell, write-node, insert-content, xlsx-insert-rows) require the resolved output path to be inside at least one `output_root`. The same canonical-path check applies.

### Invariants

- Symlink traversal cannot escape the root: `realpath` is called before comparison.
- `.` and `..` segments cannot escape: `realpath` normalizes them.
- The policies are independent: an `allowed_root` grants no write permission, and an `output_root` grants no read permission.
- When `allowed_roots` is empty, all reads are permitted. When `output_roots` is empty, all writes are permitted. Either list can be set to restrict access.

---

## 5. Domain Models and Locators

**Spec**: `openspec/specs/app-foundation/`

### Core Domain Objects (`domain/models.py`)

**`DocumentRef`** — represents one indexed Office file:
- `document_id: str` — stable UUID assigned at first index
- `path: str` — absolute file path
- `file_type: str` — `"docx"`, `"pptx"`, or `"xlsx"`
- `modified_time: float` — mtime at last index
- `content_hash: str` — SHA-256 of file bytes at last index
- `item_count: int` — number of indexed items

**`ItemRef`** — represents one addressable item within a document:
- `item_id: str` — stable item identifier / locator string
- `item_type: str` — e.g. `"paragraph"`, `"text_shape"`, `"cell"`
- `locator: str` — canonical locator string (always equals `item_id`)
- `preview: str` — truncated display text
- `metadata: dict` — format-specific attributes (style, slide number, sheet name, …)
- `content_text: str` — full item text content

**`SearchHit`** — extends `ItemRef` with:
- `score: float` — final merged relevance score (0–1)
- `matched_text: str` — highlighted match excerpt
- `match_mode: str` — `"keyword"`, `"semantic"`, or `"hybrid"`
- `scores: dict` — component scores (`keyword_score`, `semantic_score`)

**`IndexedItem`** — internal store record (not returned to callers):
- `item_id`, `item_type`, `locator`, `preview`, `content_text`, `metadata`
- Also stores `embedding: list[float] | None`

### Locator Formats

Each format uses a distinct locator grammar:

| Format | Locator pattern | Example |
|---|---|---|
| DOCX | `para:<n>` | `para:3` |
| PPTX | `slide:<n>:shape:<id>` | `slide:2:shape:4` |
| XLSX | `sheet:<name>!<coord>` | `sheet:Sales!B7` |

Locators are:
- **Stable across index refreshes** for the same document version.
- **Universal**: any locator produced by any tool (`search_documents`, `get_structure`, `get_section`, `get_node`) is directly usable as the `node_id` in `get_node` and `write_node` without transformation. This is a first-class invariant of the system.

---

## 6. Local Index Store

**Spec**: `openspec/specs/local-index-store/`

The index is a SQLite database at `index_path`. The schema is versioned; `offagent doctor` validates the schema version against the current codebase.

### Schema

```sql
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    path        TEXT UNIQUE NOT NULL,
    file_type   TEXT NOT NULL,
    modified_time REAL NOT NULL,
    content_hash  TEXT NOT NULL,
    item_count    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE items (
    item_id      TEXT NOT NULL,
    document_id  TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    item_type    TEXT NOT NULL,
    locator      TEXT NOT NULL,
    preview      TEXT NOT NULL,
    content_text TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (item_id, document_id)
);

CREATE VIRTUAL TABLE items_fts USING fts5(
    content_text,
    content='items',
    content_rowid='rowid'
);

CREATE TABLE item_embeddings (
    item_id     TEXT NOT NULL,
    document_id TEXT NOT NULL,
    embedding   BLOB NOT NULL,           -- packed float32 array
    PRIMARY KEY (item_id, document_id),
    FOREIGN KEY (item_id, document_id) REFERENCES items(item_id, document_id) ON DELETE CASCADE
);

CREATE TABLE xlsx_row_embeddings (
    document_id TEXT NOT NULL,
    sheet_name  TEXT NOT NULL,
    row_number  INTEGER NOT NULL,
    embedding   BLOB NOT NULL,
    contributing_cells TEXT NOT NULL,    -- JSON list of cell coordinates
    PRIMARY KEY (document_id, sheet_name, row_number)
);
```

### Indexing Behavior

When `index_documents(paths)` is called:
1. Each path is resolved; directories are walked recursively for `.docx`, `.pptx`, `.xlsx`.
2. For each file:
   - Compute SHA-256 hash and mtime.
   - If already indexed with the same hash and mtime: skip (no-op).
   - Otherwise: extract all items via the appropriate adapter.
3. Write `documents` record (upsert on `document_id`).
4. Delete existing `items` and `item_embeddings` for the document, then bulk-insert new items.
5. Rebuild the FTS5 index (`INSERT INTO items_fts(items_fts) VALUES('rebuild')`).
6. If `--with-embeddings`: compute and store item embeddings.
7. Emit progress events throughout (see §13).

### Content-Hash Validation

Every `DocumentRef` carries a `content_hash`. Before any write operation, the adapter re-reads the current hash of the source file and compares it to the stored hash. If they differ, the file has been modified externally since it was indexed; the operation is aborted with a `StaleLocatorError`.

---

## 7. Format Adapters

Each adapter exposes two interfaces: **extraction** (items → store) and **editing** (item-level mutations → output file).

### 7.1 DOCX Adapter

**Specs**: `docx-paragraph-extraction`, `docx-search-and-read`, `docx-paragraph-editing`, `docx-document-blocks`

**Extraction**:
- Opens with `python-docx`.
- Iterates `document.paragraphs` in order; table cells are **excluded** from the flat paragraph index (tables are separately accessible via `docx_get_tables`).
- Each paragraph becomes one `IndexedItem` with:
  - `item_type = "paragraph"`
  - `locator = f"para:{n}"` where `n` is the zero-based paragraph index
  - `metadata` includes `style_name`, `alignment`, `is_bold`, `is_italic`
  - `content_text` = full paragraph text (all runs joined)
  - `preview` = first 120 characters

**Read** (`get_node` / `read_item`):
- Re-opens the live file (not the index cache).
- Resolves `para:<n>` to `document.paragraphs[n]`.
- Returns current text and metadata.

**Replace** (`write_node`):
- Resolves the locator to the paragraph.
- Clears all runs in the paragraph.
- Adds a single new run with the replacement text (preserving the first run's character formatting as a template).
- Saves to output path (versioned or in-place).

**Append** (`insert_content` append mode):
- Resolves `after_node_id` if provided, otherwise appends at end of document body.
- Creates a new paragraph element with `add_paragraph(content, style=style_name)`.
- Returns `new_node_id = f"para:{new_index}"`.

**Table access** (`docx_get_tables`):
- Iterates `document.tables`.
- For each table: extracts rows as list-of-lists of cell text strings.
- Returns `locator` using the block-order index of the table element.

### 7.2 PPTX Adapter

**Specs**: `pptx-text-shape-extraction`, `pptx-search-and-read`, `pptx-text-shape-editing`, `pptx-slide-bundles`

**Extraction**:
- Opens with `python-pptx`.
- Iterates slides in order.
- For each slide: iterates shapes. Eligible shapes are those with a `text_frame` that contain non-empty text, **excluding** charts, tables, and picture placeholders.
- Each eligible shape becomes one `IndexedItem` with:
  - `item_type = "text_shape"`
  - `locator = f"slide:{slide_num}:shape:{shape.shape_id}"` (shape_id is the PowerPoint-internal integer ID)
  - `metadata` includes `slide_number`, `shape_name`, `placeholder_type`
  - `content_text` = full `text_frame.text`

**Read** (`get_node`):
- Resolves `slide:<n>:shape:<id>` by navigating `presentation.slides[n-1]` then finding the shape with matching `shape_id`.
- Returns current text_frame text.

**Replace** (`write_node`):
- Locates the text frame.
- Clears all paragraphs in the text frame.
- Writes the new text as a single paragraph (preserving first paragraph's format as template).

**Slide bundle** (`get_section` for PPTX):
- Returns ordered `text_blocks` list (one per eligible shape): `{locator, shape_name, text, placeholder_type}`.
- Returns `notes_text` from the slide's notes placeholder if present.
- Returns layout metadata: `layout_name`, `slide_number`.

### 7.3 XLSX Adapter

**Specs**: `xlsx-cell-extraction`, `xlsx-search-and-read`, `xlsx-cell-editing`, `xlsx-structured-table-writes`

**Extraction**:
- Opens with `openpyxl` (read-only mode for extraction).
- Iterates worksheets.
- For each worksheet: iterates all cells; skips empty cells (value is `None` and no formula).
- Each non-empty cell becomes one `IndexedItem` with:
  - `item_type = "cell"`
  - `locator = f"sheet:{sheet_name}!{coordinate}"` (e.g. `sheet:Sales!B7`)
  - `metadata` includes `sheet_name`, `coordinate`, `data_type`, `has_formula`
  - `content_text` = string representation of cell value, or formula string if formula cell

**Read** (`get_node`):
- Resolves `sheet:<name>!<coord>` by opening workbook, accessing `ws[coord]` on the named sheet.
- Returns display value and formula.

**Write cell** (`write_node`):
- Resolves the locator.
- Sets `ws[coord].value = new_value`.
- Saves to output path.
- Numeric and formula cells can be targeted; value is set as-is (string coercion only if the cell data type is string).

**Insert rows** (`xlsx_insert_rows`):
- Accepts either `rows: list[list[str]]` (positional) or `records: list[dict[str, str]]` (column-mapped by header row).
- Appends all rows to `ws.append(row_values)` in a single pass.
- Triggers **one** reindex after all rows are written (not one per row).
- Returns `first_row_locator` pointing to the first cell of the first inserted row.

**Sheet snapshot** (`get_section` for XLSX):
- Returns `cells` list: each entry has `coordinate`, `display_value`, `formula`, and `metadata`.
- Accepts optional `cell_range` (e.g. `"A1:D10"`) to limit the snapshot window.

---

## 8. Vector Search and Embeddings

**Spec**: `openspec/specs/vector-search/`

Embeddings are optional and must be explicitly enabled with `--with-embeddings` during index/reindex. When disabled, only keyword search is available.

### Embedding Provider

`adapters/embedding_provider.py` wraps [FastEmbed](https://github.com/qdrant/fastembed):
- Default model: `BAAI/bge-small-en-v1.5` (384 dimensions)
- Configurable via `embedding.model` and `embedding.dimensions`
- Embeddings are computed per-item for DOCX and PPTX
- For XLSX: per-row contextual embeddings are computed (not per-cell)

**XLSX row embeddings**: Multiple cells from the same row are concatenated as a context string and embedded together. The `xlsx_row_embeddings` table stores these embeddings plus a `contributing_cells` JSON list mapping the row embedding back to individual cell locators.

### Search Modes

**Keyword** (default): Uses SQLite FTS5 with BM25 ranking.

**Semantic**: Embeds the query at search time, computes cosine similarity against all stored item embeddings, returns top-k by score. For XLSX, computes similarity against row embeddings and expands hits to contributing cells.

**Hybrid**: Both keyword and semantic searches are executed independently. Results are merged using a weighted sum:
```
final_score = keyword_weight * keyword_score + semantic_weight * semantic_score
```
Where `keyword_weight` and `semantic_weight` are configured in `embedding.*` settings. Candidates present in only one result set receive score 0 for the missing component. After merging, results are deduplicated and sorted by `final_score` descending. The scoring is deterministic: given the same inputs, the same ranked list is always produced.

All `SearchHit` objects carry:
- `match_mode`: which search strategy was used
- `score`: final merged score
- `scores`: dict with component breakdowns (`keyword_score`, `semantic_score`)

---

## 9. Write Semantics

### 9.1 Versioned Write Outputs

**Spec**: `openspec/specs/versioned-write-outputs/`

All writes default to `output_mode="versioned"`. Versioned output naming:

```
<stem>.edited.<UTC-timestamp-ISO8601>.<ext>
```

Example: `report.docx` → `report.edited.2025-11-14T10-33-21Z.docx`

The output path is placed in the configured `output_roots` directory or, if unset, beside the source file. The `output_path` is always returned in the write result so callers know where the file was saved.

**In-place mode** (`output_mode="inplace"`): Requires `allow_inplace_overwrite = true` in config. The output file path equals the source document path. If `allow_inplace_overwrite` is `false` and `inplace` mode is requested, the system raises a `PolicyRefusedError`.

`storage/versioning.py` is the single authoritative implementation of versioned path generation. It is called by all three format adapters.

### 9.2 Stale-Locator Detection

**Spec**: `openspec/specs/stale-locator-detection/`

Before every write operation:
1. Compute the SHA-256 hash of the **current** on-disk bytes of the source document.
2. Compare against the `content_hash` stored in the `documents` index record.
3. If they differ: the document has been externally modified since last index. Raise `StaleLocatorError` with the document path, stored hash, and current hash.
4. The write is aborted before any mutations occur.

This prevents silent wrong edits when a document has been modified externally (e.g. by another process, by the user in Word/Excel/PowerPoint, or by a previous write that wasn't reindexed).

Callers must call `refresh_document` to update the index before retrying a write on a modified document.

### 9.3 Write-Reindex Synchronization

**Spec**: `openspec/specs/write-reindex-synchronization/`

Every write operation automatically reindexes the **output** document before returning. The sequence:

1. Execute the write and save to `output_path`.
2. Call `store.upsert_document(output_path)` which reindexes the output file inline.
3. Return the write result with `output_path` pointing to the now-indexed output document.

This guarantees that a write immediately followed by a search or `get_node` on the output document will see the updated content. No separate `refresh_document` call is needed after a write.

---

## 10. Application Services Layer

**Spec**: `openspec/specs/app-foundation/`

`app/services.py` is the single business logic layer shared by both the CLI and MCP interfaces. Neither interface contains business logic; they only translate inputs to service calls and format outputs.

Core `AppServices` methods:

| Method | Description |
|---|---|
| `index_documents(paths, with_embeddings)` | Walk paths, extract items, populate index |
| `refresh_document(document_id)` | Reindex one document by ID |
| `list_documents()` | Return all `DocumentRef` records |
| `search_documents(query, mode, file_type, document_id, limit)` | FTS5 / semantic / hybrid search |
| `get_structure(document_id)` | Return format-aware section outline |
| `get_section(document_id, section_id, cell_range)` | Return full section payload |
| `get_node(document_id, node_id)` | Read single leaf node from live file |
| `write_node(document_id, node_id, content, output_mode)` | Replace node content, reindex output |
| `insert_content(document_id, content, style_name, after_node_id, output_mode)` | DOCX-only paragraph insertion |
| `xlsx_insert_rows(document_id, sheet_name, rows, records, output_mode)` | XLSX-only row append |
| `docx_get_tables(document_id)` | DOCX-only table extraction |

The services layer dispatches to the appropriate format adapter based on `DocumentRef.file_type`. Format-specific operations (`insert_content`, `xlsx_insert_rows`, `docx_get_tables`) raise `UnsupportedFormatError` when called on an incompatible document type.

---

## 11. MCP Interface

**Specs**: `openspec/specs/mcp-stdio-server/`, `openspec/specs/mcp-service-tools/`, `openspec/specs/mcp-error-mapping/`

`interfaces/mcp.py` builds a [FastMCP](https://github.com/jlowin/fastmcp) server with stdio transport. Entry point: `offagent mcp [--config path]`.

### 11.1 Tool Surface (11 tools)

The MCP server exposes exactly **11 tools**. This count is a first-class acceptance criterion verified by the integration suite.

**Document management (3 tools)**:

| Tool | Inputs | Description |
|---|---|---|
| `index_documents` | `paths: list[str]`, `with_embeddings: bool = false` | Index or re-index files and directories |
| `refresh_document` | `document_id: str` | Reindex a single previously-indexed document |
| `list_documents` | _(none)_ | Return all indexed documents |

**Search (1 tool)**:

| Tool | Inputs | Description |
|---|---|---|
| `search_documents` | `query: str`, `mode: "keyword"\|"semantic"\|"hybrid" = "keyword"`, `file_type?: str`, `document_id?: str`, `limit: int = 10` | Search indexed content |

**Structure inspection (2 tools)**:

| Tool | Inputs | Description |
|---|---|---|
| `get_structure` | `document_id: str` | Format-aware section outline |
| `get_section` | `document_id: str`, `section_id: str`, `cell_range?: str` | Full section payload |

**Node access (2 tools)**:

| Tool | Inputs | Description |
|---|---|---|
| `get_node` | `document_id: str`, `node_id: str` | Read single leaf node from live file |
| `write_node` | `document_id: str`, `node_id: str`, `content: str`, `output_mode?: "versioned"\|"inplace"` | Replace node content |

**Format-specific tools (3 tools)**:

| Tool | Inputs | Description |
|---|---|---|
| `insert_content` | `document_id: str`, `content: str`, `style_name?: str`, `after_node_id?: str`, `output_mode?: str` | DOCX-only: insert paragraph |
| `xlsx_insert_rows` | `document_id: str`, `sheet_name: str`, `rows?: list[list[str]]`, `records?: list[dict]`, `output_mode?: str` | XLSX-only: append rows |
| `docx_get_tables` | `document_id: str` | DOCX-only: extract all tables |

**Tools removed from previous surface** (not registered): `locate_item`, `read_item`, `replace_text`, `append_text`, `write_cell`, `append_paragraph`, `append_row`, `replace_block`, `write_table`, `get_document_structure`, `get_document_blocks`, `get_paragraphs`, `get_presentation_structure`, `get_slide_bundle`, `get_slide_notes`, `get_workbook_structure`, `get_sheet_snapshot`, `get_block_bundle`.

### 11.2 MCP Models and Converters

`interfaces/mcp_models.py` defines Pydantic input and output models for every tool. These models:
- Are the machine-readable schema advertised to MCP clients.
- Validate all inputs before they reach the service layer.
- Are the authoritative contract tested by the MCP integration suite.

`interfaces/mcp_converters.py` transforms domain objects (`DocumentRef`, `SearchHit`, etc.) into MCP response models. Converters are pure functions with no side effects.

### 11.3 Error Mapping

**Spec**: `openspec/specs/mcp-error-mapping/`

Domain exceptions map to `fastmcp.ToolError` with structured error payloads:

| Exception | MCP error type | Message pattern |
|---|---|---|
| `DocumentNotFoundError` | `ToolError` | `"Document {id} not found in index"` |
| `ItemNotFoundError` | `ToolError` | `"Item {locator} not found in {document}"` |
| `StaleLocatorError` | `ToolError` | `"Document modified since last index: {path}"` |
| `NotEditableError` | `ToolError` | `"Item {locator} is not editable"` |
| `PolicyRefusedError` | `ToolError` | `"Access refused by policy: {path}"` |
| `UnsupportedFormatError` | `ToolError` | `"{tool} only supports {format}"` |
| `ConfigError` | `ToolError` | Config validation message |

No unhandled Python exceptions are allowed to escape the tool handlers. All `Exception` subclasses not in the above table are caught and re-raised as generic `ToolError`.

### 11.4 Universal Locator Address Space

The system guarantees a **single unified address space** across all tools. Specifically:

- Every `locator` field in a `search_documents` response is directly usable as `node_id` in `get_node` and `write_node` — no transformation needed.
- Every `locator` in a `get_structure` response is directly usable as `section_id` in `get_section`.
- Every leaf-node locator in a `get_section` response is directly usable as `node_id` in `get_node` and `write_node`.

This invariant is enforced by sharing the same locator format functions between the index adapters, structure builders, and section builders. It is verified by round-trip acceptance tests (search → get_node → write_node, and get_structure → get_section → write_node).

---

## 12. CLI Interface

**Specs**: `openspec/specs/cli-output-modes/`, `openspec/specs/document-summary-commands/`

`interfaces/cli.py` is the Typer application entry point, installed as the `offagent` command.

### 12.1 Commands

```
offagent doctor
offagent index <path> [<path>...] [--with-embeddings]
offagent reindex <path> [--with-embeddings]
offagent search <query> [--type docx|pptx|xlsx] [--doc <path>] [--mode keyword|semantic|hybrid] [--limit N]
offagent locate --doc <file> --paragraph <n>
offagent locate --doc <file> --slide <n> [--shape <id>]
offagent locate --doc <file> --sheet <name> --cell <coord>
offagent read --doc <file> --item <item-id>
offagent replace --doc <file> --item <item-id> --text <value> [--output-mode versioned|inplace]
offagent append --doc <file> --item <item-id> --text <value> [--output-mode versioned|inplace]
offagent write-cell --doc <file> --sheet <name> --cell <coord> --value <value> [--output-mode versioned|inplace]
offagent list
offagent show --doc <file> [--item <item-id>]
offagent mcp [--config <path>]
```

All commands accept `--json` and `--quiet` global flags.

### 12.2 Output Modes

**Human-readable** (default): Rich terminal formatting with section headers, tables, and inline progress bars. Designed for interactive use.

**JSON** (`--json`): Machine-readable JSON on stdout. No prose, no decorations. The JSON schema mirrors the MCP response model structure for each command. Suitable for scripting and piping.

**Quiet** (`--quiet`): Suppresses all informational and progress output. Only errors and final results are printed.

### 12.3 Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Runtime error (unhandled) |
| 2 | Invalid arguments |
| 3 | Not found / stale locator |
| 4 | Not editable |
| 5 | Policy refused |

---

## 13. Indexing Progress Reporting

**Spec**: `openspec/specs/indexing-progress-reporting/`

`app/progress.py` defines a `ProgressReporter` abstract base with two implementations:
- `CliProgressReporter` (in `interfaces/cli_progress.py`): Renders a live progress bar using Rich when the terminal is a TTY.
- `NullProgressReporter`: No-op, used by MCP and `--quiet` mode.

Progress events emitted during indexing:
- `on_start(total_files: int)`
- `on_file_start(path: str)`
- `on_file_done(path: str, item_count: int)`
- `on_embedding_start(total_items: int)`
- `on_embedding_progress(done: int, total: int)`
- `on_done(total_documents: int, total_items: int)`

The service layer receives a `ProgressReporter` as a constructor argument. This allows the CLI to pass a rich reporter and MCP to pass the null reporter without any conditional logic in the service code.

---

## 14. Document Structure Tools

**Spec**: `openspec/specs/document-structure-tools/`

Structure inspection uses two tools in a deliberate two-level hierarchy:

```
get_structure(document_id)
    → section list (top-level outline)

get_section(document_id, section_id)
    → full payload for one section
```

**DOCX structure**:
- Returns ordered blocks in document order.
- Each block has: `locator`, `block_type` (`"paragraph"` or `"table"`), `preview`, `style_name`.
- Table blocks are included in the outline with row count but without cell data (cell data is in `get_section`).

**PPTX structure**:
- Returns one entry per slide: `slide_number`, `locator`, `preview` (first shape text).

**XLSX structure**:
- Returns one entry per worksheet: `sheet_name`, `locator`, `preview` (cell A1 value), `cell_count`.

**DOCX paragraph section** (`get_section`):
- `text`: full paragraph text
- `style_name`: paragraph style
- `runs`: list of `{text, bold, italic, underline, font_size, font_name}`

**DOCX table section** (`get_section`):
- `rows`: list of lists of cell text strings
- `cell_metadata`: optional per-cell metadata

**PPTX slide section** (`get_section`):
- `text_blocks`: ordered list of `{locator, shape_name, text, placeholder_type}`
- `notes_text`: text from the notes placeholder (empty string if none)
- `layout_name`: slide layout name

**XLSX sheet section** (`get_section`):
- `cells`: list of `{coordinate, display_value, formula, metadata}`
- `cell_range`: optional parameter to limit the snapshot (e.g. `"A1:D10"`)

---

## 15. Test Coverage

### 15.1 Golden Fixture Corpus

**Spec**: `openspec/specs/golden-fixture-corpus/`

Three version-controlled fixture documents live in the test corpus:

| File | Contents |
|---|---|
| `tests/fixtures/golden.docx` | Multiple paragraphs with varying styles, bold/italic runs, two tables |
| `tests/fixtures/golden.pptx` | Multiple slides with text shapes, notes, chart and image placeholders |
| `tests/fixtures/golden.xlsx` | Multiple worksheets with string cells, numeric cells, formula cells |

These fixtures are the sole source of truth for all format-specific unit tests and MCP integration tests. Their content is fixed; tests assert against known values. Any change to a fixture must be accompanied by an update to all affected test assertions.

### 15.2 Acceptance Test Coverage

**Spec**: `openspec/specs/acceptance-test-coverage/`

The test suite covers:

**Unit tests**:
- Config parsing (TOML, env overrides, cascading precedence)
- Locator parsing and round-trip serialization
- Store CRUD, FTS5 ranking, embedding storage
- Format adapters: extraction, read, replace, append for all three formats
- Path policy: allowed-root rejection, output-root rejection, symlink escape prevention
- Versioned path generation
- Stale-locator detection (hash mismatch → abort)

**Integration tests**:
- Full index → search → read round-trips (all three formats)
- Hybrid and semantic search with mock embeddings
- Write → reindex → verify write content visible in subsequent search
- In-place mode: output path equals source
- Versioned mode: output path is a new timestamped file

**CLI acceptance tests** (all commands, all output modes):
- `--json` output parses as valid JSON with correct shape
- `--quiet` suppresses informational output
- Exit code correctness for each error scenario

**MCP integration tests**:
- Tool count: exactly 11 tools registered
- Schema validation: each tool's input schema matches `mcp_models.py`
- Round-trip: index → search → get_node → write_node (all three formats)
- Structure round-trip: get_structure → get_section → write_node
- Universal locator invariant: search locator usable in write_node without transformation
- Format-specific error: `insert_content` on PPTX returns explicit format error
- Format-specific error: `xlsx_insert_rows` on DOCX returns explicit format error

---

## 16. Data Flow Walkthrough

### Scenario: AI agent edits a paragraph in a Word document

```
1. MCP client calls: index_documents(paths=["/docs/report.docx"])
   → mcp.py handler → AppServices.index_documents()
   → path_policy: /docs/report.docx in allowed_roots? ✓
   → docx_adapter.extract_items(path)
   → store.upsert_document() + store.bulk_insert_items()
   → FTS5 rebuild
   → Returns: {document_id: "a1b2...", item_count: 42}

2. MCP client calls: search_documents(query="quarterly revenue", mode="keyword")
   → AppServices.search_documents()
   → store.fts_search("quarterly revenue", limit=10)
   → Returns: [{item_id: "para:7", locator: "para:7", preview: "Q3 quarterly revenue...", score: 0.91}]

3. MCP client calls: get_node(document_id="a1b2...", node_id="para:7")
   → AppServices.get_node()
   → docx_adapter.read_item(path, "para:7")
   → Opens live file, reads paragraph[7].text
   → Returns: {node_id: "para:7", item_type: "paragraph", text: "Q3 quarterly revenue was $4.2M", metadata: {style_name: "Normal"}}

4. MCP client calls: write_node(document_id="a1b2...", node_id="para:7", content="Q3 quarterly revenue was $4.8M", output_mode="versioned")
   → AppServices.write_node()
   → store.get_document("a1b2...") → DocumentRef{content_hash: "abc..."}
   → docx_adapter.current_hash(path) → "abc..." ✓ (no stale)
   → path_policy: output path in output_roots? ✓
   → docx_adapter.replace_paragraph(path, "para:7", "Q3 quarterly revenue was $4.8M", output_path)
   → Saves to: report.edited.2025-11-14T10-33-21Z.docx
   → store.upsert_document(output_path) ← immediate reindex
   → Returns: {output_path: "report.edited....docx", node_id: "para:7", new_text: "Q3 quarterly revenue was $4.8M", previous_text: "Q3 quarterly revenue was $4.2M"}
```

### Scenario: Structure-first navigation

```
1. get_structure(document_id="a1b2...")
   → Returns: [{locator: "para:0", block_type: "paragraph", preview: "Executive Summary", style_name: "Heading 1"},
               {locator: "para:1", block_type: "paragraph", preview: "This report covers...", style_name: "Normal"},
               {locator: "table:0", block_type: "table", preview: "3 rows × 4 cols", row_count: 3},
               ...]

2. get_section(document_id="a1b2...", section_id="table:0")
   → Returns: {block_type: "table", rows: [["Region", "Q1", "Q2", "Q3"], ["North", "1.2M", "1.4M", "1.6M"], ...]}

3. write_node(document_id="a1b2...", node_id="para:0", content="Executive Summary — Revised")
   → Same write flow as above
```

---

## 17. Error Hierarchy

`errors.py` defines the complete exception tree:

```
OffAgentError (base)
├── ConfigError                   # Misconfigured settings
├── DocumentNotFoundError         # document_id not in index
├── ItemNotFoundError             # locator not resolvable in document
├── StaleLocatorError             # content hash mismatch
├── NotEditableError              # item type does not support write
├── PolicyRefusedError            # allowed_roots / output_roots rejection
├── UnsupportedFormatError        # format-specific tool called on wrong format
└── IndexCorruptError             # schema version mismatch or corrupt DB
```

Each exception carries sufficient context for the caller to produce an actionable error message. The CLI maps each type to an exit code (§12.3). The MCP server maps each type to a structured `ToolError` (§11.3).

---

*Generated from OpenSpec corpus at `/openspec/specs/` and completed changes at `/openspec/changes/`. 