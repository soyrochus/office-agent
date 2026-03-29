## Why

Office Agent currently supports reading, searching, and editing existing documents but has no way to create new documents or apply styling. This change adds a compact, balanced set of tools for document creation and inline/block styling across DOCX, PPTX, and XLSX — closing the most critical authoring gaps without expanding the tool surface unnecessarily.

## What Changes

- Add `create_document` tool: creates a new empty DOCX, PPTX, or XLSX at a given output path
- Add `add_content_block` tool: adds a logical content unit to an existing document (paragraph, heading, table for DOCX; slide, textbox for PPTX; sheet, row, cell for XLSX)
- Add `style_inline` tool: sets character-level style properties (bold, italic, underline, font, color, etc.) on runs in DOCX/PPTX and cells/rich-text in XLSX; each specified property is written directly (overwriting any existing value); passing `null` for a property clears it back to inherited — there is no separate "remove" operation, clearing is the same call with a null value
- Add `style_block` tool: sets block-level formatting properties (alignment, indentation, spacing, cell style) on paragraphs in DOCX/PPTX and cells in XLSX; same set/overwrite/clear semantics as `style_inline`
- Add `set_structural_role` tool: sets the Word-native paragraph style on a DOCX block (heading, title, body, table header, caption), replacing whatever style was previously assigned; fails cleanly if called on PPTX or XLSX
- Add shared `InlineStyle` and `BlockStyle` data models used across all tools
- Add shared target reference models for structured locator addressing (compatible with existing typed-locator design)
- New documents integrate with the existing registration, output, and reindex flow

## Capabilities

### New Capabilities
- `document-creation`: Creating new empty DOCX, PPTX, and XLSX documents at an explicit output path, integrated with the existing versioned-write and reindex flow
- `content-block-authoring`: Adding logical content units (paragraphs, headings, tables, slides, textboxes, sheets, rows, cells) to documents via a generic block-type model
- `inline-styling`: Setting, changing, and clearing character/run-level style properties across all three formats using a shared `InlineStyle` schema; semantics follow the underlying libraries — each property is set directly or cleared to inherited via null
- `block-styling`: Setting, changing, and clearing block-level formatting properties across all three formats using a shared `BlockStyle` schema; same direct-assignment semantics as inline styling
- `docx-structural-roles`: DOCX-only structural role mapping (heading, title, body, table header, caption) via Word-native styles

### Modified Capabilities
- `versioned-write-outputs`: New documents created via `create_document` must follow the same versioned output path convention as existing writes
- `write-reindex-synchronization`: Document creation must trigger reindex in the same way that edits do

## Impact

- New modules: `models/styles.py`, `models/targets.py`, per-format adapters (`adapters/docx_adapter.py`, `adapters/pptx_adapter.py`, `adapters/xlsx_adapter.py`), tool wrappers under `tools/`
- Existing adapter and service layers extended, not replaced
- MCP tool count increases by 5 (create_document, add_content_block, style_inline, style_block, set_structural_role)
- No changes to existing read/search/edit tools or their schemas
- Dependencies: python-docx, python-pptx, openpyxl — all already in use; no new dependencies
