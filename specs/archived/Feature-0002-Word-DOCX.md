# Feature 0002 — Word (DOCX)

## Goal

Full read/write round-trip for `.docx` files: extraction, indexing, search, locate, read, replace, and append for paragraphs.

## Scope

### Included

* `adapters/docx_adapter.py` using `python-docx`:
  * extract paragraphs in document order
  * fields: paragraph index, text, style name, heading flag
  * item id format: `para:{n}`
* Index population for DOCX items via `indexing/store.py`
* `app/services.py` service methods: `index_document`, `search_corpus`, `resolve_locator`, `read_item`, `replace_item_text`, `append_item_text`
* CLI commands:
  * `office-agent index <path>` — index a file or directory
  * `office-agent reindex <path>` — force reindex a specific file
  * `office-agent search <query> [--type docx] [--doc <file>]`
  * `office-agent locate --doc <file> --paragraph <n>`
  * `office-agent read --doc <file> --item <item-id>`
  * `office-agent replace --doc <file> --item <item-id> --text "<text>"`
  * `office-agent append --doc <file> --item <item-id> --text "<text>"`

### Excluded

* Word tables, headers/footers, images, comments, tracked changes
* Versioned output (F5) — writes overwrite in-place for now or write to a temp path
* PPTX and XLSX (F3, F4)
* MCP interface (F6)

## Data Model

Item type: `paragraph`
Locator: `para:{paragraph_index}`
Fields indexed: `text`, `paragraph_index`, `style_name`, `is_heading`

## Extraction Rules

* Extract all paragraphs in document order, including empty ones (to preserve index stability)
* Style name taken from `paragraph.style.name` if available, else `None`
* Heading flag true if style name starts with `Heading`
* Table cells are skipped

## Write Rules

* `replace`: overwrite the full paragraph text, preserving the first run's character formatting
* `append`: concatenate text to the last run of the paragraph

## Acceptance Criteria

* `office-agent index ./fixtures` indexes a sample `.docx` and reports correct item count
* `office-agent search "known phrase"` returns the correct paragraph with score and preview
* `office-agent locate --doc sample.docx --paragraph 3` returns the correct `ItemRef`
* `office-agent read` returns current paragraph text from source file
* `office-agent replace` overwrites paragraph text; reopening the file confirms the change
* `office-agent append` appends text; reopening confirms
* Adapter unit tests: extract fixture, verify item count, resolve known item, patch known item, reopen and verify
