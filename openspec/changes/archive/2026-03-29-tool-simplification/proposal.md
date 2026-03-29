## Why

The current MCP surface has grown to 23 tools through incremental, format-first development: each new document format and capability got its own tool, producing a surface that forces any consumer to know too much about three different Python library internals before doing useful work. The result is fragmented structure inspection (10 tools for one concern), a dual coordinate system (`item_id` vs `block_index`) that breaks the bridge from search to write, and inconsistent naming across formats. Cutting the surface to 11 well-defined tools eliminates this accidental complexity with no loss of functional power.

## What Changes

- **BREAKING** Remove `locate_item` — superseded by `get_node`
- **BREAKING** Remove `replace_block` — superseded by `write_node` (same locator, unified address space)
- **BREAKING** Remove `append_text` — superseded by the read-compute-write pattern via `get_node` + `write_node`
- **BREAKING** Remove `get_document_structure`, `get_document_blocks`, `get_paragraphs`, `get_presentation_structure`, `get_workbook_structure` — superseded by `get_structure`
- **BREAKING** Remove `get_slide_bundle`, `get_slide_notes`, `get_block_bundle`, `get_sheet_snapshot` — superseded by `get_section`
- **BREAKING** Remove `read_item` — superseded by `get_node`
- **BREAKING** Remove `replace_text`, `write_cell` — superseded by `write_node`
- **BREAKING** Remove `append_paragraph`, `append_row`, `write_table` — superseded by `insert_content` and `xlsx_insert_rows`
- Add `get_structure` — unified format-aware document outline (DOCX blocks, PPTX slides, XLSX sheets)
- Add `get_section` — unified rich payload for one section (slide, block, or sheet), accepts any locator
- Add `get_node` — read one leaf node by locator; authoritative, not index-cached
- Add `write_node` — replace content at any node by locator, across all formats
- Add `insert_content` — insert a new DOCX paragraph at a logical position
- Add `xlsx_insert_rows` — atomic multi-row append to an XLSX worksheet (replaces `append_row` + `write_table`)
- Rename `get_tables` → `docx_get_tables` — explicit format prefix
- Enforce a single address space: all locators returned by any tool are valid as `node_id` in `get_node` and `write_node`; `block_index` as a tool API concept is eliminated

## Capabilities

### New Capabilities
- `unified-structure-access`: Specification for `get_structure` and `get_section` — the unified structural navigation layer covering all three formats
- `unified-node-access`: Specification for `get_node` and `write_node` — the universal leaf-node read/write pair and the single-address-space invariant
- `unified-content-insertion`: Specification for `insert_content`, `xlsx_insert_rows`, and `docx_get_tables` — the format-specific insertion and extraction escape hatches

### Modified Capabilities
- `mcp-service-tools`: The registered MCP tool set changes from 23 to 11 tools; tool names, schemas, and descriptions all change

## Impact

- **`src/mcp/tools/`** — most tool modules replaced or renamed; 12 tool files removed, 7 new tool files added
- **`src/mcp/server.py`** (or equivalent registration point) — tool registration list reduced from 23 to 11
- **Agent system prompt / tool descriptions** — must be updated to communicate the locator universality invariant and the new entry-point hierarchy (`get_structure` → `get_section` → `get_node`/`write_node`)
- **Existing tests** — tests for removed tools deleted; new tests cover the 11 replacement tools
- **No changes** to indexing internals, search index format, embedding pipeline, or file I/O layer
