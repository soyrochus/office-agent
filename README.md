# Office-Agent
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Server-orange.svg)](https://gofastmcp.com/getting-started/welcome)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![FOSS Pluralism](https://img.shields.io/badge/FOSS-Pluralism-purple.svg)](FOSS_PLURALISM_MANIFESTO.md)
[![OpenSpec](https://img.shields.io/badge/OpenSpec-Used-black.svg)](https://openspec.dev/)

Office-Agent (`offagent`) is a local-first Office document tool with a shared application core and a CLI entrypoint, `office-agent`.

Detailed technical implementation notes are available in [technical-implementation.md](./technical-implementation.md).

![Office Agent](./images/office-agent-small.png)

Office-Agent supports local-first workflows for `.docx`, `.pptx`, and `.xlsx` documents through both a CLI and an MCP server. The app indexes document structure into a local SQLite + FTS5 store, can optionally persist embeddings for semantic and hybrid retrieval, and routes all reads and writes through one shared service layer with path-policy enforcement, stale-locator checks, versioned outputs, and automatic reindexing.

## Current Features

### Core App

- TOML configuration with environment variable overrides
- `office-agent doctor` runtime checks for imports, SQLite, FTS5, index writability, configured roots, and vector-search readiness
- document discovery and indexing for `.docx`, `.pptx`, and `.xlsx`
- allowed-root guards for indexed reads and output-root guards for writes
- human-readable, JSON, and quiet CLI output modes
- default versioned write outputs, with optional in-place overwrite when explicitly enabled
- keyword, semantic, and hybrid search modes over indexed content

### Structured Document Model

- typed locators for DOCX, PPTX, and XLSX objects, with legacy locator compatibility where needed
- object traversal with `get_object` and `list_children`
- per-object capability reporting for `read`, `update`, `delete`, `add_child`, `move`, `copy`, and `style`
- generic object lifecycle operations: `create_object`, `update_object`, `move_object`, `copy_object`, `batch_edit`, and `delete_object`
- stale-locator detection across object and node workflows

### DOCX Support

- paragraph, run, section, table, table row, table cell, image, and page-break object resolution
- paragraph-level indexing and search with stable `para:<n>` compatibility
- node reads and writes for paragraphs and table cells
- paragraph insertion through the existing content-insert workflow
- DOCX escape hatches for paragraph style changes, page-break insertion, table creation, and table-cell merging

### PPTX Support

- presentation, slide, notes, shape, text shape, image shape, table, table row, table cell, and group-shape object resolution
- text-frame indexing and search with `slide:<n>:shape:<id>` compatibility
- node reads and writes for editable text-bearing targets
- slide move and copy operations through the generic object layer
- PPTX escape hatches for adding slides, duplicating slides, changing slide layouts, and inserting text shapes

### XLSX Support

- workbook, worksheet, row, column, cell, range, table, merged range, formula cell, and named-range object resolution
- cell-level indexing and search with `sheet:<name>!<coordinate>` compatibility
- direct cell writes plus guarded append semantics for string-compatible cells
- generic object deletion for worksheets, rows, columns, cells, and ranges where supported
- XLSX escape hatches for range writes, row insertion, column insertion, formula writes, and cell merging

### MCP Server

- stdio MCP server implemented with FastMCP
- document indexing and refresh tools
- canonical V2 search via `search_objects`, with deprecated `search_documents` alias compatibility
- structure and section tools, node read/write tools, object traversal tools, generic object mutation tools, and format-specific escape hatches
- structured MCP responses backed by the same application services used by the CLI

### Vector Search

- optional embedding generation during indexing and reindexing
- SQLite-backed embedding side tables keyed to indexed document items
- semantic retrieval over stored vectors
- hybrid retrieval that combines keyword and semantic scores
- `match_mode` and per-source score metadata in JSON and MCP search results

## Installation

The project uses `uv` in development.

```bash
uv sync
```

Run the CLI with:

```bash
uv run office-agent --help
```

## Configuration

The CLI accepts an optional config file via `--config <path>`.

Example `office-agent.toml`:

```toml
[offagent]
index_path = ".offagent/index.sqlite3"
document_roots = ["./docs"]
allowed_roots = ["./docs", "./edited"]
output_directory = "./edited"
output_roots = ["./edited", "./docs"]
allow_inplace_overwrite = true
embedding_model = "BAAI/bge-small-en-v1.5"
embedding_dimensions = 384
vector_search_top_k = 20
hybrid_keyword_weight = 0.4
hybrid_semantic_weight = 0.6
```

Environment variables override file settings:

- `OFFAGENT_CONFIG`
- `OFFAGENT_INDEX_PATH`
- `OFFAGENT_DOCUMENT_ROOTS`
- `OFFAGENT_ALLOWED_ROOTS`
- `OFFAGENT_OUTPUT_DIRECTORY`
- `OFFAGENT_OUTPUT_ROOTS`
- `OFFAGENT_ALLOW_INPLACE_OVERWRITE`
- `OFFAGENT_EMBEDDING_MODEL`
- `OFFAGENT_EMBEDDING_DIMENSIONS`
- `OFFAGENT_VECTOR_SEARCH_TOP_K`
- `OFFAGENT_HYBRID_KEYWORD_WEIGHT`
- `OFFAGENT_HYBRID_SEMANTIC_WEIGHT`

`OFFAGENT_DOCUMENT_ROOTS` uses the platform path separator, for example `:` on macOS/Linux.

Configuration fields:

- `index_path`: SQLite index file location
- `document_roots`: directories scanned by discovery and directory-based indexing
- `allowed_roots`: canonical roots allowed for indexed read operations; empty means no read guard
- `output_directory`: optional directory for versioned write outputs; defaults to the source document directory
- `output_roots`: canonical roots allowed for write outputs; if omitted and `output_directory` is set, this defaults to that directory
- `allow_inplace_overwrite`: when `true`, write commands may use `--output-mode inplace`; default is `true`
- `embedding_model`: embedding model name used when generating or querying vectors
- `embedding_dimensions`: expected vector dimensionality for the configured model
- `vector_search_top_k`: candidate pool size used by semantic and hybrid retrieval
- `hybrid_keyword_weight`: keyword contribution to hybrid ranking
- `hybrid_semantic_weight`: semantic contribution to hybrid ranking

## CLI

All commands accept `--config <path>` after the command name. Example:

```bash
uv run office-agent search "supplier shall" --config office-agent.toml
```

Structured commands also accept:

- `--json`: emit machine-readable JSON with no extra prose
- `--quiet`: suppress successful stdout output

`--json` and `--quiet` are mutually exclusive.

Write commands also accept `--output-mode <mode>` where `<mode>` is:

- `versioned`: default; writes `<name>.edited.<timestamp>.<ext>` and reindexes the new file
- `inplace`: overwrites the source file, but only if `allow_inplace_overwrite = true`

Common exit codes:

- `0`: success
- `1`: other runtime failure
- `2`: invalid arguments or incompatible flag combinations
- `3`: not-found target, missing indexed item/document, or stale-locator write failure
- `4`: not-editable target
- `5`: policy-refused operation

### Doctor

Checks runtime health, including vector-search readiness.

Options:

- `--config <path>`: optional config file path

```bash
uv run office-agent doctor
uv run office-agent doctor --config office-agent.toml
```

### Index And Reindex

`index` indexes one file or all supported Office files under a directory. `reindex` currently re-runs the same indexing flow. Add `--with-embeddings` to generate and persist embeddings during the run.

Arguments:

- `path`: file or directory to index

Options:

- `--with-embeddings`: generate embeddings for indexed items during this run
- `--config <path>`: optional config file path

```bash
uv run office-agent index ./docs
uv run office-agent index ./docs --with-embeddings
uv run office-agent index ./docs/sample.docx
uv run office-agent index ./docs/sample.pptx
uv run office-agent index ./docs/sample.xlsx
uv run office-agent reindex ./docs/sample.docx
uv run office-agent reindex ./docs/sample.docx --with-embeddings
uv run office-agent reindex ./docs/sample.pptx
uv run office-agent reindex ./docs/sample.xlsx
```

### Search

Searches indexed content through SQLite FTS5, stored embeddings, or both.

Arguments:

- `query`: search text

Options:

- `--type <docx|pptx|xlsx>`: restrict search to one document type
- `--doc <path>`: restrict search to one indexed document path
- `--mode <keyword|semantic|hybrid>`: retrieval mode; default `keyword`
- `--config <path>`: optional config file path

```bash
uv run office-agent search "supplier shall"
uv run office-agent search "supplier shall" --mode semantic
uv run office-agent search "supplier shall" --mode hybrid --json
uv run office-agent search "supplier shall" --type docx
uv run office-agent search "supplier shall" --type pptx
uv run office-agent search "supplier shall" --type xlsx
uv run office-agent search "supplier shall" --type docx --doc ./docs/sample.docx
uv run office-agent search "supplier shall" --type pptx --doc ./docs/sample.pptx
uv run office-agent search "supplier shall" --type xlsx --doc ./docs/sample.xlsx
```

Notes:

- `keyword` behaves like the original FTS-only search path
- `semantic` requires prior indexing with `--with-embeddings`
- `hybrid` combines keyword and semantic candidates and returns merged ranking metadata
- JSON output includes `match_mode` and `scores`; semantic and hybrid human-readable output also displays that metadata

### List

Lists indexed documents with document id, path, type, modified time, and indexed item count.

```bash
uv run office-agent list
uv run office-agent list --json
```

### Show

Shows one indexed document summary, or one indexed item within that document.

```bash
uv run office-agent show --doc ./docs/sample.docx
uv run office-agent show --doc ./docs/sample.docx --item para:3
uv run office-agent show --doc ./docs/sample.xlsx --item sheet:Budget2026!B12 --json
```

### Locate

Resolves a direct item reference for one document.

Options:

- `--doc <path>`: required document path
- `--paragraph <n>`: DOCX-only paragraph lookup
- `--slide <n>`: PPTX-only slide lookup
- `--shape <id>`: optional PPTX shape narrowing; only valid with `--slide`
- `--sheet <name>`: XLSX-only worksheet lookup
- `--cell <coordinate>`: XLSX-only cell coordinate; only valid with `--sheet`
- `--config <path>`: optional config file path

Valid option combinations:

- DOCX: `--doc` + `--paragraph`
- PPTX: `--doc` + `--slide` with optional `--shape`
- XLSX: `--doc` + `--sheet` + `--cell`

```bash
uv run office-agent locate --doc ./docs/sample.docx --paragraph 3
uv run office-agent locate --doc ./docs/sample.pptx --slide 1
uv run office-agent locate --doc ./docs/sample.pptx --slide 1 --shape 7
uv run office-agent locate --doc ./docs/sample.xlsx --sheet Budget2026 --cell B12
```

### Read

Reads the current source content for one indexed item.

Options:

- `--doc <path>`: required document path
- `--item <item-id>`: required item id
- `--config <path>`: optional config file path

```bash
uv run office-agent read --doc ./docs/sample.docx --item para:3
uv run office-agent read --doc ./docs/sample.pptx --item slide:1:shape:7
uv run office-agent read --doc ./docs/sample.xlsx --item sheet:Budget2026!B12
```

### Replace

Replaces the full text of one DOCX paragraph or PPTX text shape.

Options:

- `--doc <path>`: required document path
- `--item <item-id>`: required item id
- `--text <value>`: replacement text
- `--output-mode <versioned|inplace>`: write mode; default `versioned`
- `--config <path>`: optional config file path

Notes:

- `replace` is supported for DOCX and PPTX only
- XLSX uses `write-cell` instead of `replace`

```bash
uv run office-agent replace --doc ./docs/sample.docx --item para:3 --text "Updated paragraph text."
uv run office-agent replace --doc ./docs/sample.pptx --item slide:1:shape:7 --text "Updated slide text."
uv run office-agent replace --doc ./docs/sample.docx --item para:3 --text "Updated paragraph text." --output-mode versioned
```

### Append

Appends text to one supported target.

Options:

- `--doc <path>`: required document path
- `--item <item-id>`: required item id
- `--text <value>`: appended text
- `--output-mode <versioned|inplace>`: write mode; default `versioned`
- `--config <path>`: optional config file path

Notes:

- DOCX appends to the target paragraph
- PPTX appends to the target text frame
- XLSX appends only to empty or string-compatible cells
- stale-locator failures exit with code `3`

```bash
uv run office-agent append --doc ./docs/sample.docx --item para:3 --text " Additional text."
uv run office-agent append --doc ./docs/sample.pptx --item slide:1:shape:7 --text "\nAdditional slide text."
uv run office-agent append --doc ./docs/sample.xlsx --item sheet:Notes!A1 --text " Additional note."
```

### Write Cell

Writes one XLSX cell value directly.

Options:

- `--doc <path>`: required `.xlsx` document path
- `--sheet <name>`: required worksheet name
- `--cell <coordinate>`: required cell coordinate
- `--value <value>`: new cell value
- `--output-mode <versioned|inplace>`: write mode; default `versioned`
- `--config <path>`: optional config file path

```bash
uv run office-agent write-cell --doc ./docs/sample.xlsx --sheet Budget2026 --cell B12 --value "125000"
uv run office-agent write-cell --doc ./docs/sample.xlsx --sheet Budget2026 --cell B12 --value "125000" --output-mode inplace
```

### MCP

Starts the FastMCP server on stdio.

Options:

- `--config <path>`: optional config file path

```bash
uv run office-agent mcp
uv run office-agent mcp --config office-agent.toml
```

The MCP server exposes these tools:

- `index_documents(paths)`
- `refresh_document(document_id)`
- `list_documents()`
- `search_objects(query, file_type=None, document_id=None, mode="keyword", limit=20)`
- `search_documents(...)` as a deprecated alias for pre-V2 consumers
- `get_structure(document_id)`
- `get_section(document_id, section_id, cell_range=None)`
- `get_node(document_id, node_id)`
- `write_node(document_id, node_id, content, output_mode="versioned")`
- `insert_content(document_id, content, style_name=None, after_node_id=None, output_mode="versioned")`
- `docx_get_tables(document_id)`
- `get_object(document_id, locator)`
- `list_children(document_id, locator, child_type=None, limit=None)`
- `create_object(document_id, parent_locator, object_type, properties, position=None, output_mode="versioned")`
- `update_object(document_id, locator, properties, output_mode="versioned")`
- `move_object(document_id, locator, new_parent_locator, position=None, output_mode="versioned")`
- `copy_object(document_id, locator, target_parent_locator, position=None, output_mode="versioned")`
- `batch_edit(document_id, operations, output_mode="versioned", dry_run=False)`
- `delete_object(document_id, locator, output_mode="versioned")`
- `docx_set_paragraph_style(document_id, locator, style_name, output_mode="versioned")`
- `docx_insert_page_break(document_id, locator, output_mode="versioned")`
- `docx_add_table(document_id, row_count, column_count, position=None, column_widths=None, style_name=None, output_mode="versioned")`
- `docx_merge_table_cells(document_id, start_locator, end_locator, output_mode="versioned")`
- `pptx_add_slide(document_id, layout_index=None, layout_name=None, output_mode="versioned")`
- `pptx_duplicate_slide(document_id, locator, position=None, output_mode="versioned")`
- `pptx_set_slide_layout(document_id, locator, layout_index=None, layout_name=None, output_mode="versioned")`
- `pptx_add_text_shape(document_id, locator, text, left, top, width, height, output_mode="versioned")`
- `xlsx_write_range(document_id, locator, values, output_mode="versioned")`
- `xlsx_insert_rows(...)` for both append-rows compatibility mode and worksheet row insertion mode
- `xlsx_insert_columns(document_id, locator, column_index, count, output_mode="versioned")`
- `xlsx_set_formula(document_id, locator, formula, output_mode="versioned")`
- `xlsx_merge_cells(document_id, locator, output_mode="versioned")`

## Example query session

![QUery session](./images/mcp-query.png)

## Item Id Reference

Use these item-id formats with `read`, `replace`, and `append`:

- DOCX: `para:<n>`
- PPTX: `slide:<slide-number>:shape:<shape-id>`
- XLSX: `sheet:<worksheet-name>!<cell-coordinate>`

## Write Behavior

By default, all write commands create a versioned output file:

- `sample.docx` -> `sample.edited.20260318-214512345678.docx`
- `deck.pptx` -> `deck.edited.20260318-214512345678.pptx`
- `budget.xlsx` -> `budget.edited.20260318-214512345678.xlsx`

After a successful write:

- the output file is automatically reindexed
- CLI output reports the written output path
- search results can resolve against the new version immediately
- managed output roots are treated as readable workflow roots so versioned-write follow-up commands continue to work

If the source file changed after indexing:

- the service compares the current file hash to the indexed `content_hash`
- it tries to re-resolve the same item id against the current file
- if that fails, the command exits with stale-locator error code `3`

## Development

Run the test suite with:

```bash
uv run pytest
```

This repository also includes an example skill for Office-document workflows at [`.github/skills/office-agent`](./.github/skills/office-agent/). The location is VSCode specific but it should work for Claude Code and Codex as well.  

Acceptance coverage uses checked-in golden Office fixtures under [`tests/fixtures`](./tests/fixtures/), including DOCX, PPTX, and XLSX documents exercised by the CLI and FastMCP integration suites.

The test suite is written in `pytest` and includes:

- configuration and diagnostics coverage
- path-policy coverage
- SQLite store coverage
- DOCX adapter tests
- DOCX service workflow tests
- PPTX adapter tests
- PPTX service workflow tests
- XLSX adapter tests
- XLSX service workflow tests
- CLI round-trip and acceptance tests for DOCX, PPTX, and XLSX
- FastMCP stdio integration and acceptance tests for the MCP tool surface
- CLI/MCP parity tests for the core index → search → locate → read → replace workflow

## Project Status

Implemented:

- shared CLI/application-core structure
- configuration and doctor checks
- allowed-root and output-root policy enforcement
- SQLite index bootstrap and FTS5-backed search
- embedding-backed semantic and hybrid retrieval with mode-aware CLI/MCP output
- DOCX paragraph extraction and editing workflow
- PPTX text-shape extraction and editing workflow
- XLSX cell extraction and editing workflow
- indexed document summary commands (`list` and `show`)
- JSON and quiet CLI output modes
- versioned write outputs with automatic reindex
- stale-locator protection for write commands
- MCP interface over stdio with FastMCP

Not implemented yet:

- SSE or streamable HTTP MCP transports
- MCP resources and prompts
- richer locator resolution beyond the current direct DOCX, PPTX, and XLSX flows


## Principles of Participation

Everyone is invited and welcome to contribute: open issues, propose pull requests, share ideas, or help improve documentation. Participation is open to all, regardless of background or viewpoint.  

This project follows the [FOSS Pluralism Manifesto](./FOSS_PLURALISM_MANIFESTO.md),  
which affirms respect for people, freedom to critique ideas, and space for diverse perspectives.  

## License and Copyright

Copyright (c) 2026, Iwan van der Kleijn

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
