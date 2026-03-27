# Architecture Guidelines — offagent

## 1. Governing Principle

CLI and MCP are interfaces, not applications. The real product is a shared application core with a local structural index and deterministic patch operations. No business logic belongs in the interface layer.

---

## 2. Technology Stack

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python 3.11+ | Required by all three Office libraries |
| Package name | `offagent` | Short, importable; CLI command is `office-agent` |
| CLI framework | Typer | Structured subcommands, type-annotated params, help generation |
| MCP SDK | Official MCP Python SDK (stdio) | Direct support for tools/resources over standard transports |
| Word | `python-docx` | Paragraphs, runs, styles; create and update `.docx` |
| PowerPoint | `python-pptx` | Slides, shapes, text frames |
| Excel | `openpyxl` | Workbook, worksheet, cell object model |
| Search | SQLite FTS5 | Local, zero-dependency, sufficient for modest corpora |
| Data validation | Pydantic | Shared models across CLI and MCP tool schemas |
| XML safety | `defusedxml` | Guard against malicious Office XML if untrusted input is expected |

---

## 3. Module Structure

```
src/offagent/
├── config.py               # Config loader — file + env var overrides
├── domain/
│   ├── models.py           # DocumentRef, ItemRef, SearchHit, PatchOperation
│   └── locators.py         # Locator parsing and normalisation
├── indexing/
│   ├── store.py            # SQLite schema, connection management, FTS queries
│   └── extractors.py       # Format-agnostic extraction orchestration
├── adapters/
│   ├── docx_adapter.py     # python-docx extraction and patching
│   ├── pptx_adapter.py     # python-pptx extraction and patching
│   └── xlsx_adapter.py     # openpyxl extraction and patching
├── app/
│   └── services.py         # All use-case logic; the authoritative behaviour boundary
├── storage/
│   └── versioning.py       # Versioned output path generation
└── interfaces/
    ├── cli.py              # Typer app, subcommand groups, output formatting
    └── mcp.py              # MCP server, tool registrations, error mapping
```

Each layer may only call inward. Interfaces call services. Services call adapters and the index store. Adapters call only their respective libraries. No adapter may call another adapter.

---

## 4. Layered Architecture

```
┌─────────────────────────────────┐
│  Interface layer (CLI / MCP)    │  ← thin; format, route, present
├─────────────────────────────────┤
│  Application service layer      │  ← all use-case logic lives here
├─────────────────────────────────┤
│  Document adapter layer         │  ← format-specific extract + patch
├─────────────────────────────────┤
│  Index layer (SQLite FTS5)      │  ← search substrate; never at query time scan files
├─────────────────────────────────┤
│  File / versioning layer        │  ← source files are read-only inputs by default
└─────────────────────────────────┘
```

**Rule:** if you find yourself writing a query-time loop over workbook cells or slide shapes, you are in the wrong layer. That work belongs in the extraction phase.

---

## 5. Domain Model

### Core types

**`DocumentRef`**
```
document_id   : str   # stable UUID or hash-based id
path          : str
file_type     : "docx" | "pptx" | "xlsx"
display_name  : str
modified_time : datetime
content_hash  : str
```

**`ItemRef`**
```
document_id : str
item_id     : str
item_type   : str
locator     : str
preview     : str
```

**`SearchHit`**
```
document_id  : str
item_id      : str
score        : float
matched_text : str
locator      : str
item_type    : str
preview      : str
```

**`PatchOperation`**
```
patch_id       : str
document_id    : str
item_id        : str
operation_type : "replace_text" | "append_text" | "write_value"
payload        : str
dry_run        : bool
output_path    : str | None
```

### Item identifiers by format

| Format | item_type | item_id example |
|--------|-----------|-----------------|
| DOCX | `paragraph` | `para:17` |
| PPTX | `slide_text_shape` | `slide:3:shape:7` |
| XLSX | `cell` | `sheet:Budget2026!B12` |

Item ids must be stable between index runs as long as the document structure has not changed. They are the join key between search results and patch operations.

---

## 6. Locator Model

Two classes of locator are supported.

**Direct locators** bypass search when unambiguous:
- `paragraph 17`
- `slide 3`, `slide 3 shape 2`
- `sheet Budget2026 cell B12`

**Search-derived locators** hit the FTS index first, then resolve to an `ItemRef`:
- "the paragraph containing supplier shall"
- "the slide mentioning Azure migration"

All write operations must resolve to a concrete `ItemRef` before the patch is applied. The locator is never passed directly to a write.

---

## 7. Index Design

### Schema

**`documents`**
```sql
document_id   TEXT PRIMARY KEY,
path          TEXT NOT NULL,
file_type     TEXT NOT NULL,
display_name  TEXT,
modified_time TEXT,
content_hash  TEXT,
is_active     INTEGER DEFAULT 1
```

**`items`**
```sql
item_id       TEXT PRIMARY KEY,
document_id   TEXT REFERENCES documents(document_id),
item_type     TEXT,
locator_json  TEXT,
preview       TEXT,
metadata_json TEXT
```

**`items_fts`** (FTS5 virtual table)
```sql
item_id TEXT,
text    TEXT
```

### Search flow

1. Query FTS5 with user query
2. Retrieve matching `item_id`s
3. Join to `items` and `documents`
4. Rank and return `SearchHit[]`

Never scan source files at query time.

### Indexing behaviour

- Detect changed files via content hash or modified timestamp
- Full re-extraction on change; partial updates are not supported in MVP
- Mark deleted files as `is_active = 0`; do not purge rows

---

## 8. Adapter Contracts

Each adapter must implement exactly two operations:

1. **Extract** — open the source file, yield canonical items conforming to the domain model
2. **Patch** — open the source file, apply one `PatchOperation`, write to the specified output path

Adapters must not call the index, call other adapters, or produce side effects beyond writing the patched output file.

### Extraction rules by format

**DOCX**
- Unit: paragraph (in document order)
- Skip: table cells, headers/footers, images, comments
- Heading flag: true if `paragraph.style.name` starts with `"Heading"`

**PPTX**
- Unit: text-bearing shapes only (`shape.has_text_frame == True`)
- Skip: charts, tables, images, SmartArt, non-text shapes
- Concatenate text frame paragraphs with `\n` for index text

**XLSX**
- Unit: non-empty cells (value or formula present)
- Index text: `str(cell.value)`, truncated to configured max length
- Formula cells: record formula text in `formula` field; use formula text as display string

---

## 9. Write Semantics

### Replace

| Format | Behaviour |
|--------|-----------|
| DOCX | Replace full paragraph text; preserve first run's character formatting |
| PPTX | Replace full text frame text; set on first paragraph, clear remaining |
| XLSX | Set `cell.value` directly; attempt type coercion (int → float → str) |

### Append

| Format | Behaviour |
|--------|-----------|
| DOCX | Concatenate text to last run of paragraph |
| PPTX | Append text to text frame, optionally preceded by `\n` |
| XLSX | Allowed only if cell contains a string value or is empty; otherwise reject with exit code 4 |

### Stale locator detection

Before every patch:
1. Load source file
2. Compare `content_hash` against indexed value
3. If mismatch: attempt re-resolution of item id in updated content
4. If item no longer resolves: fail with "stale locator" (exit code 3)

---

## 10. Versioning Policy

Default behaviour for every write:

1. Compute output path: `<name>.edited.<YYYYMMDD-HHMMSSffffff>.<ext>` (UTC, sortable)
2. Write patched document to output path
3. Reindex output file immediately
4. Return output path, change summary, and new document id/version

`output_mode` values:
- `"versioned"` — default; write to versioned sibling or configured output directory
- `"inplace"` — overwrite source; only permitted if `allow_inplace_overwrite = true` in config

Source files are never modified unless `inplace` mode is explicitly permitted and requested.

---

## 11. Interface Layer Rules

### CLI

- Framework: Typer
- All subcommands that return structured data must support `--json` and `--quiet` flags
- Human-readable output is the default; `--json` output must parse as valid JSON
- Exit codes are mandatory and must be consistent across all commands:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Operational failure |
| 2 | Invalid arguments |
| 3 | Target not found |
| 4 | Target not editable |
| 5 | Patch refused by policy |

### MCP

- Transport: stdio only for MVP
- Tool schemas are derived from the same Pydantic models used by the service layer
- Tool implementations are one-liners: validate input → call service → return result
- Errors map to structured MCP error responses with descriptive messages
- No business logic in `interfaces/mcp.py`

---

## 12. Configuration

Config is loaded from a file (e.g. `offagent.toml` or `offagent.yaml`) with environment variable overrides for individual keys. Environment variables alone are not sufficient as the sole config mechanism.

Required config keys:

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `indexed_roots` | list[str] | `[]` | Directories to index |
| `output_directory` | str | same as source | Where versioned files are written |
| `allow_inplace_overwrite` | bool | `false` | Permit `inplace` output mode |
| `file_include_globs` | list[str] | `["*.docx","*.pptx","*.xlsx"]` | Included file patterns |
| `file_exclude_globs` | list[str] | `[]` | Excluded file patterns |
| `max_indexed_cell_text_length` | int | `500` | Truncation limit for XLSX cell text |
| `max_search_hits` | int | `20` | Default result limit |
| `log_level` | str | `"INFO"` | Logging verbosity |

---

## 13. Security Constraints

These are not optional and must be enforced at the service layer, not at the interface layer:

1. All file paths are normalised (resolve symlinks, collapse `..`) before any operation
2. Reads are rejected if the normalised path falls outside `indexed_roots`
3. Writes are rejected if the normalised output path falls outside the configured output roots
4. No file deletion in any code path in the MVP
5. No macro execution
6. No embedded-object processing
7. No external link dereferencing
8. Use `defusedxml` for XML parsing when handling untrusted Office files

---

## 14. Observability

Log the following events at INFO level minimum:

- File discovered
- File indexed (with item count)
- Extraction error (with file path and exception)
- Search query executed (with query and hit count)
- Locator resolved (with item id)
- Patch applied (with item id and operation type)
- Output written (with output path)
- Reindex completed (with document id)

The `doctor` command validates the runtime environment:
- Required libraries importable
- SQLite available and FTS5 enabled
- Index path writable
- All configured `indexed_roots` readable
- MCP server starts without error

---

## 15. Testing Strategy

All tests are written with **pytest**. No other test framework is permitted. Use `pytest` for unit tests, adapter tests, CLI tests, and MCP integration tests. Test discovery follows standard pytest conventions (`tests/` directory, files named `test_*.py`).

### Fixture corpus (`tests/fixtures/`)

Three files, version-controlled, never regenerated between runs:
- `sample.docx` — 10+ paragraphs including headings; no tables
- `sample.pptx` — 3+ slides with title, subtitle, text box, and at least one non-text shape
- `sample.xlsx` — 2+ sheets with text cells, numeric cells, and one formula cell

### Test layers

| Layer | Scope |
|-------|-------|
| Unit | Locator parsing, version path generation, content hash comparison, stale locator detection, patch request validation |
| Adapter | Extract fixture → verify item count → resolve known item → patch known item → reopen output → verify content. One suite per format. |
| CLI | All command groups against fixture corpus; exit code assertions for every defined failure mode. Use `typer.testing.CliRunner` invoked from pytest. |
| MCP | Start server as subprocess; invoke each tool; validate schema and result structure; full round-trip cycle |

CLI tests are part of the primary test harness. The CLI must be testable without mocking the service layer.

---

## 16. What Does Not Belong Here (MVP Exclusions)

These items are explicitly out of scope and must not be designed around:

- Word tables, headers/footers, comments, tracked changes
- PowerPoint layout manipulation, new shapes/slides, notes pages
- Excel formulas as semantic objects, merged regions, pivot tables, charts
- Embeddings or vector search
- Collaborative locking or multi-user conflict resolution
- HTTP API
- `diff_versions`, `batch_replace`, `summarize_document` MCP tools
- MCP resources and prompts
