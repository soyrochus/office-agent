## 1. Domain Models

- [x] 1.1 Add `InlineStyle` frozen dataclass to `domain/models.py` (bold, italic, underline, strike, font_name, font_size, font_color, highlight)
- [x] 1.2 Add `BlockStyle` frozen dataclass to `domain/models.py` (alignment, indent_level, left_indent, right_indent, spacing_before, spacing_after, line_spacing, wrap_text, vertical_alignment, fill_color, number_format)
- [x] 1.3 Update `docx_adapter.RunFormatting` to delegate to / align with `InlineStyle` so the two definitions do not diverge

## 2. DOCX Adapter

- [x] 2.1 Add `create_docx(output_path)` — writes an empty DOCX using python-docx's default template (includes standard Word styles)
- [x] 2.2 Add `add_paragraph(document_path, text, output_path)` — appends a plain paragraph
- [x] 2.3 Add `add_heading(document_path, text, level, output_path)` — appends a paragraph with "Heading {level}" style
- [x] 2.4 Add `add_table(document_path, rows, columns, output_path)` — appends an empty table (extends existing `docx_add_table` logic or reuses it)
- [x] 2.5 Add `style_run(document_path, locator, style: InlineStyle, clear_fields, output_path)` — patch-applies inline style to the targeted run
- [x] 2.6 Add `style_paragraph(document_path, locator, style: BlockStyle, clear_fields, output_path)` — patch-applies block style to the targeted paragraph
- [x] 2.7 Add `set_structural_role(document_path, locator, role, level, output_path)` — maps role → Word style name, validates style exists in catalog, applies it

## 3. PPTX Adapter

- [x] 3.1 Add `create_pptx(output_path)` — writes an empty PPTX with a default slide layout master
- [x] 3.2 Add `add_slide(document_path, output_path)` — appends an empty slide (reuse/extend existing `pptx_add_slide` logic)
- [x] 3.3 Add `add_textbox(document_path, slide_locator, text, left, top, width, height, output_path)` — adds a text shape with defaults when geometry is omitted (reuse/extend `pptx_add_text_shape`)
- [x] 3.4 Add `style_run(document_path, locator, style: InlineStyle, clear_fields, output_path)` — patch-applies inline style to the targeted PPTX run
- [x] 3.5 Add `style_paragraph(document_path, locator, style: BlockStyle, clear_fields, output_path)` — patch-applies block style to the targeted PPTX paragraph

## 4. XLSX Adapter

- [x] 4.1 Add `create_xlsx(output_path, initial_sheet_name)` — writes an empty workbook with one sheet; default sheet name is "Sheet1"
- [x] 4.2 Add `add_sheet(document_path, name, output_path)` — adds a new worksheet
- [x] 4.3 Add `add_row(document_path, sheet_locator, values, output_path)` — writes values to the next available row
- [x] 4.4 Add `write_cell(document_path, cell_locator, value, output_path)` — sets a cell value (extend existing write_cell if present)
- [x] 4.5 Add `style_cell_inline(document_path, locator, style: InlineStyle, clear_fields, output_path)` — applies font properties to the full cell (bold, italic, font_name, font_size, font_color)
- [x] 4.6 Add `style_cell_block(document_path, locator, style: BlockStyle, clear_fields, output_path)` — applies alignment, wrap_text, vertical_alignment, fill_color, number_format to the cell

## 5. Service Layer

- [x] 5.1 Add `create_document(format, output_path, output_mode)` to `AppServices` — validates format, calls the appropriate adapter create function, calls `show_document` to register and index the result, returns `MutationResult`
- [x] 5.2 Add `add_content_block(document_id, block_type, properties, output_mode)` to `AppServices` — dispatches on `(file_type, block_type)`, calls the appropriate adapter function, follows versioned-output + reindex flow
- [x] 5.3 Add `style_inline(document_id, locator, style, clear_fields, output_mode)` to `AppServices` — resolves locator, dispatches on file_type to the appropriate adapter style_run function, follows versioned-output + reindex flow
- [x] 5.4 Add `style_block(document_id, locator, style, clear_fields, output_mode)` to `AppServices` — resolves locator, dispatches on file_type to the appropriate adapter style_paragraph/cell function, follows versioned-output + reindex flow
- [x] 5.5 Add `set_structural_role(document_id, locator, role, level, output_mode)` to `AppServices` — guards DOCX-only via `_require_document_type`, calls docx adapter, follows versioned-output + reindex flow

## 6. MCP Layer

- [x] 6.1 Add Pydantic request models to `mcp_models.py`: `CreateDocumentRequest`, `AddContentBlockRequest`, `StyleInlineRequest`, `StyleBlockRequest`, `SetStructuralRoleRequest`
- [x] 6.2 Add `InlineStyleModel` and `BlockStyleModel` Pydantic models (nested in request models; `extra="forbid"` to reject unknown fields)
- [x] 6.3 Add `create_document` MCP tool to `mcp.py`
- [x] 6.4 Add `add_content_block` MCP tool to `mcp.py`
- [x] 6.5 Add `style_inline` MCP tool to `mcp.py`
- [x] 6.6 Add `style_block` MCP tool to `mcp.py`
- [x] 6.7 Add `set_structural_role` MCP tool to `mcp.py`

## 7. Tests

- [x] 7.1 Test `create_document` for each format: file is created, has correct extension, is indexed, returns valid `document_id`
- [x] 7.2 Test `create_document` DOCX: standard Word styles present in style catalog
- [x] 7.3 Test `create_document` XLSX: default sheet "Sheet1" present; optional `initial_sheet_name` respected
- [x] 7.4 Test `add_content_block` for each supported `(format, block_type)` pair: block is present in written output
- [x] 7.5 Test `add_content_block` invalid combination raises `InvalidArgumentsError`
- [x] 7.6 Test `style_inline` on DOCX run: bold, italic, font_name, font_color set correctly
- [x] 7.7 Test `style_inline` on PPTX run: at least one inline property applied
- [x] 7.8 Test `style_inline` on XLSX cell: font properties applied to full cell
- [x] 7.9 Test `style_inline` `clear_fields`: property is set to None/inherited after clear
- [x] 7.10 Test `style_block` on DOCX paragraph: alignment and spacing applied
- [x] 7.11 Test `style_block` on PPTX paragraph: alignment or indent_level applied
- [x] 7.12 Test `style_block` on XLSX cell: wrap_text, alignment, fill_color applied
- [x] 7.13 Test `set_structural_role` for each supported role on DOCX: correct Word style assigned
- [x] 7.14 Test `set_structural_role` with `role="heading"` and valid level: "Heading {level}" style assigned
- [x] 7.15 Test `set_structural_role` on PPTX raises `InvalidArgumentsError`
- [x] 7.16 Test `set_structural_role` on XLSX raises `InvalidArgumentsError`
- [x] 7.17 Test `set_structural_role` with missing `level` for heading raises `InvalidArgumentsError`
- [x] 7.18 Test that all five new tools follow versioned-output + reindex flow (output path in result, document re-queryable after call)
