## Why

The current MCP tool surface covers discovery and leaf-node updates well, but lacks the object lifecycle operations (create, delete, move, copy, batch) required for practical office-document authoring and restructuring workflows. Tools V2 closes this gap by introducing a generic object-lifecycle layer above `python-docx`, `python-pptx`, and `openpyxl` while fully preserving the existing indexing, search, and embedding subsystem.

## What Changes

- Introduce a generic object-lifecycle MCP core: `get_object`, `list_children`, `create_object`, `update_object`, `delete_object`, `move_object`, `copy_object`, `batch_edit`
- Introduce stable typed locators (e.g. `docx:para:12`, `pptx:slide:4:shape:7`, `xlsx:sheet:Revenue!B12`) as the universal address scheme across all tools
- Introduce per-object capability reporting so agents can discover valid operations without guessing
- Replace `search_documents` with `search_objects`, which returns locators directly usable in object operations — **BREAKING** for callers consuming the raw search result schema
- Add DOCX format-specific escape hatches: `docx_set_paragraph_style`, `docx_insert_page_break`, `docx_add_table`, `docx_merge_table_cells`
- Add PPTX format-specific escape hatches: `pptx_add_slide`, `pptx_duplicate_slide`, `pptx_set_slide_layout`, `pptx_add_text_shape`
- Add XLSX format-specific escape hatches: `xlsx_write_range`, `xlsx_insert_rows`, `xlsx_insert_columns`, `xlsx_set_formula`, `xlsx_merge_cells`
- Preserve `index_documents`, `refresh_document`, `list_documents`, keyword/semantic/hybrid search, embeddings, and all output modes unchanged

## Capabilities

### New Capabilities

- `object-lifecycle-core`: Generic MCP tool set for object inspection, traversal, mutation, and batched editing across all three formats
- `object-capability-model`: Per-object capability advertisement (`read`, `update`, `delete`, `add_child`, `move`, `copy`, `style`) returned on every object response
- `docx-object-operations`: DOCX object model (paragraph, run, table, image, section) and format-specific escape hatch tools
- `pptx-object-operations`: PPTX object model (slide, shape, notes, table, group) and format-specific escape hatch tools
- `xlsx-object-operations`: XLSX object model (worksheet, row, column, cell, range, named_range) and format-specific escape hatch tools

### Modified Capabilities

- `mcp-service-tools`: `search_documents` is superseded by `search_objects`, which returns `locator`, `object_type`, and `match_mode` in every hit in addition to existing fields; the legacy tool name may be aliased for compatibility

## Impact

- `src/tools/` — new tool handlers for all object-lifecycle and format-specific tools
- `src/locators/` — new typed locator model and stale-locator validation integrated across all mutation tools
- `src/objects/` — new per-format object model layer bridging the MCP surface to `python-docx`, `python-pptx`, and `openpyxl`
- MCP tool schema — tool list expands from ~10 to ~25 tools; `search_documents` result schema changes (**BREAKING**)
- Existing specs `stale-locator-detection`, `versioned-write-outputs`, `write-reindex-synchronization` remain correct; `mcp-service-tools` requires a delta spec
