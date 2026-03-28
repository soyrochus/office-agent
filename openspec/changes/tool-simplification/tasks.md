## 1. Remove deprecated tool handlers

- [ ] 1.1 Remove `locate_item` and `read_item` handler functions from `mcp.py`
- [ ] 1.2 Remove `get_document_structure`, `get_document_blocks`, and `get_paragraphs` handler functions from `mcp.py`
- [ ] 1.3 Remove `get_presentation_structure`, `get_slide_bundle`, and `get_slide_notes` handler functions from `mcp.py`
- [ ] 1.4 Remove `get_workbook_structure`, `get_sheet_snapshot`, and `get_block_bundle` handler functions from `mcp.py`
- [ ] 1.5 Remove `replace_text`, `append_text`, `replace_block`, and `write_cell` handler functions from `mcp.py`
- [ ] 1.6 Remove `append_paragraph`, `append_row`, and `write_table` handler functions from `mcp.py`

## 2. Remove deprecated models and converters

- [ ] 2.1 Remove input/output Pydantic models for all deprecated tools from `mcp_models.py`
- [ ] 2.2 Remove converter functions for all deprecated tools from `mcp_converters.py`

## 3. Add service layer methods for new tools

- [ ] 3.1 Add `get_structure(document_id)` service method: dispatches to format-specific structure builders and returns a uniform section list with locators
- [ ] 3.2 Add `get_section(document_id, section_id, cell_range=None)` service method: dispatches by file_type and returns format-specific section payload
- [ ] 3.3 Add `get_node(document_id, node_id)` service method: reads a single leaf node from the live file, returns `node_id`, `item_type`, `text`, `metadata`
- [ ] 3.4 Add `write_node(document_id, node_id, content, output_mode)` service method: resolves locator, replaces content, re-indexes output document, returns write result
- [ ] 3.5 Add `insert_content(document_id, content, style_name, after_node_id, output_mode)` service method for DOCX; raise explicit error for non-DOCX
- [ ] 3.6 Add `xlsx_insert_rows(document_id, sheet_name, rows, records, output_mode)` service method for XLSX; raise explicit error for non-XLSX
- [ ] 3.7 Rename/refactor `get_tables` service method to `docx_get_tables`; add explicit non-DOCX error

## 4. Add new MCP tool handlers and models

- [ ] 4.1 Add `get_structure` tool handler, input model (`document_id`), and output model (section list with locator, format-specific fields)
- [ ] 4.2 Add `get_section` tool handler, input model (`document_id`, `section_id`, optional `cell_range`), and output model (union of DOCX/PPTX/XLSX section payloads)
- [ ] 4.3 Add `get_node` tool handler, input model (`document_id`, `node_id`), and output model (`node_id`, `item_type`, `text`, `metadata`)
- [ ] 4.4 Add `write_node` tool handler, input model (`document_id`, `node_id`, `content`, optional `output_mode`), and output model (`output_path`, `node_id`, `new_text`, `previous_text`)
- [ ] 4.5 Add `insert_content` tool handler, input model (`document_id`, `content`, optional `style_name`, `after_node_id`, `output_mode`), and output model (`output_path`, `new_node_id`, `preview`)
- [ ] 4.6 Add `xlsx_insert_rows` tool handler, input model (`document_id`, `sheet_name`, optional `rows`/`records`, optional `output_mode`), and output model (`output_path`, `rows_inserted`, `first_row_locator`)
- [ ] 4.7 Add `docx_get_tables` tool handler, input model (`document_id`), and output model (list of tables with `locator`, `table_index`, `rows`, `preview`)

## 5. Verify locator address space invariant

- [ ] 5.1 Confirm that `get_structure` section locators for DOCX are the same format as `item_id` values produced by the search index for equivalent nodes
- [ ] 5.2 Confirm that `get_section` leaf node locators are valid as `node_id` inputs to `write_node` for all three formats
- [ ] 5.3 Fix any locator format mismatches found in 5.1–5.2 so a single address space is maintained

## 6. Tests for new tools

- [ ] 6.1 Add tests for `get_structure` covering DOCX (paragraph and table blocks), PPTX (slides), and XLSX (worksheets); assert locator presence on each section entry
- [ ] 6.2 Add tests for `get_section` covering DOCX paragraph block (text/style/runs), DOCX table block (rows), PPTX slide (text_blocks, notes_text), and XLSX sheet (cells with coordinate/formula)
- [ ] 6.3 Add test for `get_section` XLSX `cell_range` parameter: assert response contains only cells within the specified range
- [ ] 6.4 Add tests for `get_node` across DOCX, PPTX, and XLSX; assert returned text matches live file content
- [ ] 6.5 Add tests for `write_node` in versioned and inplace modes across DOCX, PPTX, and XLSX; assert `previous_text` is correct and output document is re-indexed
- [ ] 6.6 Add test for universal locator invariant: search → `get_node` → `write_node` round-trip using the locator from a search hit without transformation
- [ ] 6.7 Add test for universal locator invariant: `get_structure` → `get_section` → `write_node` round-trip using locators from structure inspection
- [ ] 6.8 Add tests for `insert_content`: append at end, insert after node, apply style, and explicit error for PPTX/XLSX
- [ ] 6.9 Add tests for `xlsx_insert_rows`: positional rows, column-mapped records, single reindex after multi-row insert, and explicit error for DOCX/PPTX
- [ ] 6.10 Add tests for `docx_get_tables`: all tables returned with rows, locator valid for `get_section`, explicit error for PPTX/XLSX

## 7. Delete tests for removed tools

- [ ] 7.1 Delete test cases for `locate_item`, `read_item`, `get_document_structure`, `get_document_blocks`, `get_paragraphs`
- [ ] 7.2 Delete test cases for `get_presentation_structure`, `get_slide_bundle`, `get_slide_notes`, `get_workbook_structure`, `get_sheet_snapshot`, `get_block_bundle`
- [ ] 7.3 Delete test cases for `replace_text`, `append_text`, `replace_block`, `write_cell`, `append_paragraph`, `append_row`, `write_table`

## 8. Acceptance verification

- [ ] 8.1 Verify the MCP server reports exactly 11 tool definitions when queried for its schema
- [ ] 8.2 Run the full MCP integration/acceptance suite against the golden fixture corpus and confirm all tests pass
- [ ] 8.3 Update the agent system prompt to document the 11-tool surface, the locator universality invariant, and the `get_structure` → `get_section` → `get_node`/`write_node` navigation hierarchy
