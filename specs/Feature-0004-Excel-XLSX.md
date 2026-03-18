# Feature 0004 — Excel (XLSX)

## Goal

Full read/write round-trip for `.xlsx` files: cell extraction, indexing, search, locate, read, and write-cell.

## Scope

### Included

* `adapters/xlsx_adapter.py` using `openpyxl`:
  * traverse all worksheets
  * extract all non-empty cells (value or formula present)
  * fields: sheet name, cell coordinate, raw value, formula text if present, display string for indexing
  * item id format: `sheet:{sheet_name}!{coordinate}` e.g. `sheet:Budget2026!B12`
* Index population for XLSX items
* Service layer extended to handle `xlsx` item types and `write_value` operation
* CLI commands:
  * `office-agent index` / `office-agent reindex` — extended to handle `.xlsx`
  * `office-agent search <query> [--type xlsx] [--doc <file>]`
  * `office-agent locate --doc <file> --sheet <name> --cell <coordinate>`
  * `office-agent read --doc <file> --item <item-id>`
  * `office-agent write-cell --doc <file> --sheet <name> --cell <coordinate> --value "<value>"`
  * `office-agent append --doc <file> --item <item-id> --text "<text>"` (string-compatible cells only)

### Excluded

* Formulas as structured edits — formula text is indexed as text only
* Merged-region semantics
* Table resizing, chart objects, pivot tables
* Excel append to numeric/formula cells — must be rejected with exit code 4 and a message directing user to use `write-cell`
* DOCX and XLSX (separate features)
* Versioned output (F5)
* MCP interface (F6)

## Data Model

Item type: `cell`
Locator: `sheet:{sheet_name}!{coordinate}`
Fields indexed: `display_string`, `sheet_name`, `coordinate`, `raw_value`, `formula`

## Extraction Rules

* Skip cells where both `cell.value` is `None` and `cell.data_type` is not formula
* `display_string` for indexing: use `str(cell.value)`, truncated to max configured length
* Formula cells: record formula text as-is in `formula` field; use formula text as display string
* Sheet name taken from `worksheet.title`

## Write Rules

* `write_cell`: set `cell.value` directly; accept numeric strings and attempt type coercion (int, float, then string)
* `append`: allowed only if existing cell value is a string or cell is empty; otherwise reject with exit code 4
* Path traversal guard: sheet name must not contain path separators

## Acceptance Criteria

* `office-agent index ./fixtures` indexes a sample `.xlsx` and reports correct non-empty cell count
* `office-agent search "known text"` returns correct cell hit with sheet and coordinate
* `office-agent locate --doc sample.xlsx --sheet Sheet1 --cell B12` returns correct `ItemRef`
* `office-agent read` returns current cell value from source
* `office-agent write-cell` updates cell value; reopening file confirms change
* Attempting `append` on a numeric cell returns exit code 4 with informative message
* Adapter unit tests: extract fixture, verify item count, resolve known cell, patch known cell, reopen and verify
