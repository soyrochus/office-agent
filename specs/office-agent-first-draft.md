Below is a concrete implementation specification for a dual-interface Office document tool with CLI first and MCP second. The core design decision is this: CLI and MCP are only interfaces. The real product is a shared application core with a local structural index and deterministic patch operations. That is the only way to keep latency acceptable for Word, PowerPoint, and Excel. The standard Python libraries support reading and writing those formats, but they are not indexed search systems. `python-docx` is for creating and updating `.docx`, `python-pptx` exposes slide shapes and text frames, and `openpyxl` exposes workbook, worksheet, and cell models rather than high-level search. MCP in Python is well supported through the official SDK, and FastMCP has been incorporated into that ecosystem; FastMCP also now ships CLI-oriented capabilities such as discovery, invocation, and CLI generation, which reinforces the value of a dual-interface design. ([GitHub][1])

## 1. Purpose

Build a local-first Office document interaction tool for three file types:

* Word `.docx`
* PowerPoint `.pptx`
* Excel `.xlsx`

The tool must support two interfaces over the same internal engine:

* CLI interface for local use, testing, scripting, and operational debugging
* MCP interface for agentic use from clients such as ChatGPT-compatible tooling, IDE agents, or local agent runtimes

HTTP API is explicitly out of scope for the first release, but the architecture must not block it later.

## 2. MVP scope

The MVP is intentionally narrow.

Supported operations:

* Search information across indexed Office documents
* Locate a specific item directly or via search results
* Read the content of that located item
* Modify an existing item
* Append text to an existing item

Supported editable item types:

* Word: paragraph only
* PowerPoint: existing text-bearing shape only
* Excel: single cell only

Explicitly out of scope in the MVP:

* Word tables
* Excel table-aware updates
* Excel formulas as semantic objects
* PowerPoint layout manipulation
* New PowerPoint shapes or slides
* Images, charts, comments, footnotes, notes pages, headers/footers
* Embeddings, vector search, semantic indexing
* Collaborative locking or multi-user conflict resolution
* HTTP API

## 3. Product principles

The design should follow six constraints.

First, search must never scan full documents at query time unless operating in a fallback debug mode. Query-time traversal through workbook cells or slide shapes would be too slow and too verbose over MCP.

Second, search and editing must be separated. Search operates on a local extracted index. Edit operations resolve back to the source file and patch exactly one known target.

Third, all interfaces must share one domain core. CLI and MCP are adapters, not separate applications.

Fourth, all write operations must be deterministic and narrow. There should be no generic “rewrite document” command in the MVP.

Fifth, writes must create versioned outputs by default. Silent in-place overwrite is too risky for agentic use.

Sixth, the system must expose stable location identifiers so that an agent can search, cite, locate, and then patch the same item.

## 4. High-level architecture

The system consists of five layers.

### 4.1 Interface layer

Two front doors:

* `office-agent` CLI executable
* MCP server process

Both call the same application services.

### 4.2 Application service layer

This layer exposes use-case operations such as:

* index files
* search corpus
* resolve locator
* read item
* replace item text
* append item text
* save versioned output

This layer is the authoritative behavior boundary.

### 4.3 Document adapter layer

Format-specific adapters:

* DOCX adapter using `python-docx`
* PPTX adapter using `python-pptx`
* XLSX adapter using `openpyxl`

These adapters do two things only:

* extract canonical searchable units from native files
* apply deterministic patches back to native files

The underlying libraries are a fit for this because they already expose paragraphs and runs for Word, text frames and shapes for PowerPoint, and worksheets and cells for Excel. Not all PowerPoint shapes have text frames, which is exactly why the MVP should reject non-text shapes for edit operations. ([Python-Docx][2])

### 4.4 Index layer

A local SQLite database with FTS5 is the search substrate.

Two logical stores:

* metadata tables
* extracted text index

This is not optional. None of the Office libraries provide cross-document indexed search in the form you need, and `openpyxl` in particular is a workbook object model rather than a search engine. ([Python-Docx][2])

### 4.5 File/versioning layer

Source files remain canonical inputs. Modified files are written as versioned siblings or into a designated output directory.

## 5. Canonical data model

The internal model should be format-neutral where possible.

### 5.1 Core identifiers

`DocumentRef`

* `document_id`: stable UUID or hash-based id
* `path`
* `file_type`: `docx | pptx | xlsx`
* `display_name`
* `modified_time`
* `content_hash`

`ItemRef`

* `document_id`
* `item_id`
* `item_type`
* `locator`
* `preview`

`SearchHit`

* `document_id`
* `item_id`
* `score`
* `matched_text`
* `locator`
* `item_type`
* `preview`

`PatchOperation`

* `patch_id`
* `document_id`
* `item_id`
* `operation_type`: `replace_text | append_text | write_value`
* `payload`
* `dry_run`
* `output_path`

### 5.2 Format-specific canonical items

For DOCX:

* `paragraph`
* item ids like `para:17`

Canonical fields:

* paragraph index
* paragraph text
* style name if available
* heading level if applicable

For PPTX:

* `slide_text_shape`
* item ids like `slide:3:shape:7`

Canonical fields:

* slide number
* shape index / id
* shape name if available
* text frame content
* whether shape is placeholder

For XLSX:

* `cell`
* item ids like `sheet:Budget2026!B12`

Canonical fields:

* sheet name
* cell coordinate
* raw value
* formula if present
* display string for indexing
* defined name or table membership if easily derivable later

## 6. Locator model

The system supports two locator classes.

### 6.1 Direct locators

Examples:

* `slide 3`
* `slide 3 shape 2`
* `paragraph 17`
* `sheet Budget2026 cell B12`

These bypass search when unambiguous.

### 6.2 Search-derived locators

Examples:

* “the slide mentioning Azure migration”
* “the paragraph containing supplier shall”
* “the cell containing Acciona in workbook cost-model.xlsx”

These hit the index first, then resolve to stable item ids.

The tool should always normalize to `ItemRef` before any write.

## 7. Functional specification

### 7.1 Indexing

Goal: ingest Office files into a local searchable representation.

Behavior:

* discover files under a root path or from explicit paths
* detect changed files via content hash or modified timestamp
* extract searchable items
* update metadata and FTS index
* mark deleted files as inactive or purge them

CLI command examples:

* `office-agent index ./docs`
* `office-agent reindex ./docs/presentation.pptx`

MCP tools:

* `index_documents`
* `refresh_document`

Expected outputs:

* number of files scanned
* number indexed
* number skipped
* errors with file paths

### 7.2 Search

Goal: query the local corpus quickly.

Search modes:

* plain full-text
* file-type filtered
* path filtered
* direct document-scoped search

CLI examples:

* `office-agent search "Q4 revenue"`
* `office-agent search "supplier shall" --type docx`
* `office-agent search "budget variance" --doc budget.xlsx`

MCP tool:

* `search_documents(query, file_type=None, document_id=None, limit=20)`

Output:

* ranked `SearchHit[]`

### 7.3 Locate

Goal: resolve a known target without free-text search.

CLI examples:

* `office-agent locate --doc pitch.pptx --slide 3`
* `office-agent locate --doc spec.docx --paragraph 17`
* `office-agent locate --doc budget.xlsx --sheet Budget2026 --cell B12`

MCP tool:

* `locate_item(document_id, locator)`

Output:

* exact `ItemRef`
* preview content
* item metadata

### 7.4 Read

Goal: retrieve current content of a resolved item from source.

CLI examples:

* `office-agent read --doc pitch.pptx --item slide:3:shape:7`
* `office-agent read --doc budget.xlsx --sheet Budget2026 --cell B12`

MCP tool:

* `read_item(document_id, item_id)`

Output:

* current source content
* locator metadata
* editability flag

### 7.5 Replace text / write value

Goal: overwrite an item’s content deterministically.

CLI examples:

* `office-agent replace --doc spec.docx --item para:17 --text "New paragraph text"`
* `office-agent replace --doc pitch.pptx --item slide:3:shape:7 --text "Updated title"`
* `office-agent write-cell --doc budget.xlsx --sheet Budget2026 --cell B12 --value "125000"`

MCP tools:

* `replace_text(document_id, item_id, new_text, output_mode="versioned")`
* `write_cell(document_id, sheet, cell, value, output_mode="versioned")`

Output:

* output file path
* change summary
* reindexed document id/version

### 7.6 Append text

Goal: append new text to an existing text item.

CLI examples:

* `office-agent append --doc report.docx --item para:17 --text " Additional sentence."`
* `office-agent append --doc pitch.pptx --item slide:3:shape:7 --text "\nSecond line."`

MCP tool:

* `append_text(document_id, item_id, text_to_add, output_mode="versioned")`

Excel append should be treated cautiously. In the MVP, append for Excel should be allowed only when the target cell is string-compatible. Otherwise reject and require `write_cell`.

### 7.7 Save policy

Default behavior:

* save versioned copy
* reindex changed output
* do not overwrite source unless explicitly requested and permitted by config

Version naming convention:

* `<name>.edited.<timestamp>.<ext>`

## 8. Interface specification

## 8.1 CLI interface

The CLI is the primary operational surface for local testing and debugging.

### CLI goals

* direct human usability
* scriptability in shell pipelines
* machine-readable JSON output
* feature parity with core MCP tools where feasible

### CLI command groups

`index`

* index paths
* refresh index

`search`

* query corpus
* optional output formats: table, json

`locate`

* resolve direct locators

`read`

* inspect current content

`replace`

* overwrite text-bearing target

`append`

* append text to target

`write-cell`

* set Excel cell value

`list`

* list indexed documents

`show`

* show document summary or item details

`doctor`

* validate environment, libraries, and index health

### CLI output modes

* human-readable default
* `--json`
* `--quiet`

### CLI exit codes

* `0` success
* `1` operational failure
* `2` invalid arguments
* `3` target not found
* `4` target not editable
* `5` patch refused by policy

### CLI framework

Use Typer or Click. Typer is a good fit because it gives structured subcommands, type-annotated parameters, and help generation while staying lightweight. This is an architectural recommendation rather than a requirement from a source.

## 8.2 MCP interface

The MCP surface exposes the same capabilities as tools. MCP’s Python SDK supports building servers that expose tools, resources, and prompts over standard transports, which matches this design directly. ([GitHub][1])

### MCP transport scope

For the first release:

* stdio required
* SSE or streamable HTTP optional later, not required

The official SDK supports standard transports such as stdio, SSE, and Streamable HTTP, so the design should not hard-code a single transport in the application core. ([GitHub][1])

### MCP tools

Required tools:

* `index_documents`
* `refresh_document`
* `list_documents`
* `search_documents`
* `locate_item`
* `read_item`
* `replace_text`
* `append_text`
* `write_cell`

Optional later:

* `summarize_document`
* `diff_versions`
* `batch_replace`

### MCP resources

Useful resources, optional in MVP:

* indexed document list
* document summaries
* server capabilities
* schema/version info

### MCP prompts

Out of scope for MVP unless needed for demo quality. They are not necessary for the underlying product.

## 9. Shared application core

The application core should be packaged as a reusable Python library, for example:

`office_agent_core`

Suggested internal modules:

* `app.services`
* `domain.models`
* `domain.locators`
* `indexing.extractors`
* `indexing.store`
* `adapters.docx_adapter`
* `adapters.pptx_adapter`
* `adapters.xlsx_adapter`
* `interfaces.cli`
* `interfaces.mcp`
* `storage.versioning`
* `config`

The CLI and MCP layers should each be thin.

## 10. Extraction specification by format

### 10.1 DOCX extraction

Use `python-docx` to load the document and extract paragraphs in document order. `python-docx` exposes paragraphs and text runs and can create and update `.docx` files. It also exposes tables, but those are out of scope in the MVP. ([Python-Docx][2])

MVP extraction unit:

* paragraph

Fields indexed:

* text
* paragraph index
* style name
* heading flag if style indicates heading

Editable:

* yes, full paragraph text only

Rejected:

* table cells
* headers/footers
* images
* comments
* tracked changes

### 10.2 PPTX extraction

Use `python-pptx` to traverse slides and shapes. Text in PowerPoint lives in text frames, and not all shapes have a text frame. This makes shape-level filtering mandatory. ([python-pptx][3])

MVP extraction unit:

* text-bearing shape on a slide

Fields indexed:

* slide number
* shape id/index
* shape name
* text frame text

Editable:

* yes, if `has_text_frame`

Rejected:

* charts
* tables
* images
* SmartArt
* non-text shapes
* layout edits

### 10.3 XLSX extraction

Use `openpyxl` to inspect workbook, worksheets, and cells. The extraction model is cell-oriented in the MVP, but indexing should flatten cells into searchable rows instead of forcing query-time iteration. `openpyxl` is appropriate for workbook and cell access; it is not a high-level search layer. ([GitHub][1])

MVP extraction unit:

* single cell with non-empty value or formula

Fields indexed:

* sheet name
* cell coordinate
* value text
* formula text if present
* workbook path

Editable:

* yes, direct value write

Rejected:

* merged-region semantics
* formulas as structured edits
* table resizing
* chart objects
* pivot tables

## 11. Index design

Use SQLite with:

* `documents` table
* `items` table
* FTS5 virtual table for searchable text

Suggested schema outline:

`documents`

* `document_id`
* `path`
* `file_type`
* `display_name`
* `modified_time`
* `content_hash`
* `is_active`

`items`

* `item_id`
* `document_id`
* `item_type`
* `locator_json`
* `preview`
* `metadata_json`

`items_fts`

* `item_id`
* `text`

Search flow:

1. query FTS
2. fetch matching `item_id`s
3. join back to items and documents
4. rank and return hits

This gives low-latency search without embeddings.

## 12. Write semantics

Write behavior must be explicit and conservative.

### Replace semantics

Word:

* replace entire paragraph text

PowerPoint:

* replace full text frame text

Excel:

* replace cell value

### Append semantics

Word:

* append plain text to paragraph

PowerPoint:

* append plain text to existing text frame, optionally with newline

Excel:

* append only if existing cell contains text or is empty and target mode is string; otherwise reject

### Conflict behavior

If source file changed since indexing:

* reload source
* verify target still resolves
* apply patch if same target exists
* otherwise fail with “stale locator”

## 13. Configuration

Config file example conceptually:

* indexed roots
* output directory
* overwrite policy
* file include/exclude globs
* max indexed cell text length
* max search hits
* logging level

Environment variables only for overrides, not as sole config.

## 14. Observability and diagnostics

The MVP needs strong diagnostics because document formats are messy.

Required logging events:

* file discovered
* file indexed
* extraction error
* search query executed
* locator resolved
* patch applied
* output written
* reindex completed

Add a `doctor` command to validate:

* required libraries import
* SQLite availability
* index path writable
* document path readable
* MCP server start sanity

## 15. Testing strategy

Because CLI is first-class, the CLI becomes part of the test harness.

### Unit tests

* locator parsing
* canonical item generation
* version naming
* patch request validation
* stale target detection

### Format adapter tests

For each file type:

* extract sample document
* verify expected item count
* resolve known item
* patch known item
* reopen output and verify content

### CLI tests

* `index`
* `search`
* `locate`
* `read`
* `replace`
* `append`
* `write-cell`

### MCP tests

* start server
* invoke each tool
* validate tool schema and result structure

### Golden test fixtures

Create a small fixture corpus:

* one `.docx` with headings and paragraphs
* one `.pptx` with title/subtitle/text boxes
* one `.xlsx` with a few sheets and text/value cells

These fixtures should remain deliberately simple and stable.

## 16. Security and safety

The system is local-first, but still needs guardrails.

Minimum controls:

* configurable allowed root directories
* path normalization
* deny writes outside allowed output roots
* no arbitrary file deletion in MVP
* no macro execution
* no embedded-object processing
* no external link dereferencing

For Excel/XML parsing more broadly, untrusted Office XML deserves caution. Earlier official documentation around `openpyxl` has noted XML security concerns and recommends hardened parsing approaches such as `defusedxml` in relevant contexts. That should be adopted if you expect untrusted input. ([Python-Docx][2])

## 17. Packaging and deployment

Recommended project structure:

* Python package with console entry point
* optional separate `mcp_server.py`
* one shared config loader
* one local SQLite index per workspace or profile

Suggested executable names:

* CLI: `office-agent`
* MCP mode: `office-agent mcp` or separate `office-agent-mcp`

A single binary entrypoint with submodes is cleaner operationally.

## 18. Recommended implementation sequence

Phase 1 should be CLI-first but with MCP-ready service boundaries.

### Phase 1A

* project skeleton
* config
* SQLite schema
* document discovery
* DOCX extraction
* CLI index/search/read

### Phase 1B

* PPTX extraction
* direct slide/shape locate
* CLI replace/append for text shapes

### Phase 1C

* XLSX extraction
* direct cell locate
* CLI write-cell

### Phase 1D

* MCP server wrapper over existing services
* stdio transport
* tool schemas
* integration tests

### Phase 1E

* versioning
* reindex-after-write
* diagnostics and doctor command

### Phase 1F

* golden fixture corpus: one `.docx`, one `.pptx`, one `.xlsx` — deliberately simple and stable
* CLI `list` and `show` commands
* `--json` and `--quiet` output modes across all CLI commands
* standardised exit codes (0 success, 1 operational failure, 2 invalid arguments, 3 not found, 4 not editable, 5 patch refused)
* security path guards: allowed root validation, path normalisation, deny writes outside output roots
* full CLI test suite covering all command groups against fixture corpus
* full MCP integration test suite covering all tool schemas and result structures against fixture corpus

This order is better than starting with MCP because it gives you a fast debug surface and a reliable test rig.

## 19. Acceptance criteria for MVP

The MVP is done when all of these are true.

* A user can index a directory of `.docx`, `.pptx`, and `.xlsx` files from the CLI.
* A user can search across those files in under acceptable local latency for a modest corpus.
* A user can directly locate paragraph, slide text item, or cell by explicit locator.
* A user can read the current content of that item.
* A user can replace or append text to Word paragraphs and PowerPoint text shapes.
* A user can write a value into an Excel cell.
* Every write creates a versioned output file by default.
* The changed file is reindexed automatically.
* The MCP server exposes equivalent operations as tools.
* CLI and MCP both rely on the same underlying services.

## 20. Concrete recommendation

Do not start by trying to make MCP itself solve search. It should not. Build the CLI and core indexing engine first, then expose the same capabilities via MCP. That gives you a usable local tool even before the agentic layer is polished, and it keeps the architecture clean.



[1]: https://github.com/modelcontextprotocol/python-sdk?utm_source=chatgpt.com "MCP Python SDK"
[2]: https://python-docx.readthedocs.io/?utm_source=chatgpt.com "python-docx — python-docx 1.2.0 documentation"
[3]: https://python-pptx.readthedocs.io/en/latest/user/text.html?utm_source=chatgpt.com "Working with text — python-pptx 1.0.0 documentation"


## 21 Addedum - Naming

Given your ecosystem and need for practicality:

Python package: offagent
CLI command: office-agent

Internal short alias (optional): offagt

This gives you:
uv add offagent
office-agent search "Q4 revenue"

And in Python:

from offagent import search, index

No friction, no weird abbreviations, no loss of meaning.

Important detail (often missed)

Your package name, CLI name, and module import do NOT have to match exactly.

You can define in pyproject.toml:

package name: offagent

console script: office-agent

So users never see the compromise.