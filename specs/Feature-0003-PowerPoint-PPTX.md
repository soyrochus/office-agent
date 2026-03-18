# Feature 0003 — PowerPoint (PPTX)

## Goal

Full read/write round-trip for `.pptx` files: extraction of text-bearing shapes, indexing, search, locate, replace, and append for slide text shapes.

## Scope

### Included

* `adapters/pptx_adapter.py` using `python-pptx`:
  * traverse slides and shapes
  * extract only shapes where `shape.has_text_frame` is true
  * fields: slide number, shape id, shape index, shape name, text frame text, is_placeholder flag
  * item id format: `slide:{slide_number}:shape:{shape_id}`
* Index population for PPTX items
* Service layer extended to handle `pptx` item types
* CLI commands:
  * `office-agent index` / `office-agent reindex` — extended to handle `.pptx`
  * `office-agent search <query> [--type pptx] [--doc <file>]`
  * `office-agent locate --doc <file> --slide <n> [--shape <id>]`
  * `office-agent read --doc <file> --item <item-id>`
  * `office-agent replace --doc <file> --item <item-id> --text "<text>"`
  * `office-agent append --doc <file> --item <item-id> --text "<text>"`

### Excluded

* Charts, tables, images, SmartArt, non-text shapes — these must be explicitly rejected with exit code 4
* Slide layout manipulation
* New shapes or slides
* Notes pages
* DOCX and XLSX (separate features)
* Versioned output (F5)
* MCP interface (F6)

## Data Model

Item type: `slide_text_shape`
Locator: `slide:{slide_number}:shape:{shape_id}`
Fields indexed: `text_frame_text`, `slide_number`, `shape_id`, `shape_name`, `is_placeholder`

## Extraction Rules

* Skip shapes without `has_text_frame`
* Concatenate all paragraph texts in text frame with newline separator for indexing
* Shape name taken from `shape.name` if available

## Write Rules

* `replace`: replace full text frame text; set text on first paragraph of the text frame, clear remaining paragraphs
* `append`: append plain text to the existing text frame, optionally preceded by a newline if caller supplies `\n` prefix
* Reject write on any shape that does not `has_text_frame` with error "target not editable" (exit code 4)

## Acceptance Criteria

* `office-agent index ./fixtures` indexes a sample `.pptx` and reports correct text-shape item count
* Non-text shapes are not indexed and are rejected on locate/read with exit code 4
* `office-agent search "known phrase" --type pptx` returns the correct shape hit
* `office-agent locate --doc sample.pptx --slide 2` returns matching `ItemRef`(s) for that slide
* `office-agent read` returns current text frame content from source
* `office-agent replace` overwrites text frame; reopening confirms
* `office-agent append` appends text; reopening confirms
* Adapter unit tests: extract fixture, verify item count, resolve known shape, patch known shape, reopen and verify
