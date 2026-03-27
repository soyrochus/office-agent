# Feature 0009 — Optimize Vector Search for XLSX

## Goal

Reduce the cost of XLSX semantic indexing by stopping per-cell embeddings for every populated cell. Instead, embed only text-like XLSX cells, group them by row into row-level embedding units, and preserve enough source-cell metadata for the search layer to recover precise workbook locations.

## Scope

### Included

#### Text-like cell filtering for vector indexing

* Keep existing XLSX extraction for locate/read/write and keyword indexing
* For semantic indexing only, exclude cells that are not text-like
* "Text-like" means the cell display text is non-empty and contains meaningful alphabetic text rather than only numeric, currency, percentage, or date-like content
* Formula cells may still participate when their indexed display text is text-like

#### Row-level XLSX embedding units

* Stop generating one embedding per XLSX cell
* Build one embedding input per worksheet row that contains at least one text-like cell
* A row embedding input is composed from:
  * workbook name
  * sheet name
  * row number
  * ordered cell snippets such as `<coordinate>: <display_text>`
* Rows remain sheet-local; no cross-sheet chunking

#### Source metadata preserved for search resolution

* Every row embedding unit must retain source metadata for the cells that contributed to it
* Required metadata per contributing cell:
  * `item_id`
  * `sheet_name`
  * `coordinate`
  * `display_text`
* Search must use this metadata to resolve a semantic or hybrid hit back to real workbook locations
* The canonical editable/searchable location remains the existing cell locator format: `sheet:{sheet_name}!{coordinate}`

#### Search behaviour

* Keyword search remains unchanged and still operates over the normal cell-level indexed items
* Semantic and hybrid search for XLSX use row-level embeddings as the retrieval unit
* A row-level semantic match must still return result metadata that identifies the contributing source cells and allows the interface layer to display or choose a precise workbook location
* Search previews for XLSX semantic hits should prefer the matched row text and expose the source coordinates involved

#### Performance intent

* XLSX semantic indexing cost should scale with the number of text-bearing rows, not the total number of populated cells
* Numeric-heavy financial sheets should become substantially cheaper to embed

### Excluded

* Changes to DOCX or PPTX embedding granularity
* Removal of cell-level items from the main index
* Table detection or semantic grouping beyond worksheet rows
* Automatic header inference or schema learning
* Approximate nearest-neighbour indexing

## Module Structure Changes

```
src/offagent/
├── adapters/
│   └── xlsx_adapter.py          # MODIFIED — text-like filter + row embedding payload builder
├── app/
│   └── services.py              # MODIFIED — XLSX embedding path uses row units instead of cell units
├── domain/
│   └── models.py                # MODIFIED — semantic hit metadata may expose source-cell locations
└── indexing/
    └── store.py                 # MODIFIED — persist row-embedding source metadata or equivalent mapping
```

## Data Model

### Existing cell items remain

The `items` table and XLSX `ItemRef` contract remain cell-based:

* item type: `cell`
* item id: `sheet:{sheet_name}!{coordinate}`
* locate/read/write continue to target the original cell

### New row embedding metadata

Each XLSX embedding record should represent a row-level semantic unit and retain:

* `document_id`
* `sheet_name`
* `row_number`
* `source_item_ids`
* `source_coordinates`
* `source_display_texts`

The exact storage layout may be a new sidecar table or an extension of the existing embedding metadata scheme, but the mapping from row embedding back to source cells must be explicit and queryable.

## Embedding Construction Rules

### Text-like filter

* Include cells whose display text contains useful alphabetic tokens
* Exclude cells whose display text is empty or effectively numeric-only
* Preserve the original cell item in the normal index even if it is excluded from semantic embedding

### Row embedding text

For each eligible worksheet row:

```text
Workbook: <workbook-name>
Sheet: <sheet-name>
Row: <row-number>
Cells:
- <coordinate>: <display_text>
- <coordinate>: <display_text>
...
```

Cells must appear in worksheet column order.

## Search Resolution Rules

* A semantic XLSX hit must carry enough metadata for the system to determine the contributing cell locations
* The interface layer must be able to render sheet name and coordinates from the hit without reopening the workbook
* If a row embedding contains multiple candidate cells, the hit metadata should expose all contributing coordinates so a later ranking or UI rule can choose the most relevant cell

## Acceptance Criteria

* Indexing an XLSX with many numeric cells and relatively few textual cells produces far fewer embeddings than the count of populated cells
* Semantic XLSX search still returns hits with valid sheet-and-cell location metadata
* Keyword XLSX search results remain unchanged
* `office-agent locate`, `read`, `write-cell`, and `append` continue to operate on cell-level locators
* Tests cover:
  * text-like cell filtering
  * row payload generation in stable column order
  * mapping from row embedding hit back to source cell metadata
  * reduced embedding count for numeric-heavy worksheets
