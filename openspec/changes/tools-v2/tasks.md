## 1. Typed Locator Grammar

- [x] 1.1 Extend `domain/locators.py` to parse fully-qualified V2 locators (`docx:`, `pptx:`, `xlsx:` prefixes with nested path components)
- [x] 1.2 Ensure short-form legacy locators (`para:N`, `slide:N:S`, `sheet!A1`) remain valid and resolve correctly alongside V2 forms
- [x] 1.3 Add locator serialization helpers that emit fully-qualified V2 locator strings from adapter-internal identifiers
- [x] 1.4 Add unit tests for V2 locator parsing, round-trip serialization, and legacy locator compatibility

## 2. Object Layer Foundation

- [x] 2.1 Create `src/offagent/objects/` package with `base.py` defining the `ObjectResolver` protocol (get_object, list_children, resolve_capabilities)
- [x] 2.2 Define `ObjectPayload`, `ChildSummary`, `MutationResult`, and `BatchResult` dataclasses in `domain/models.py`
- [x] 2.3 Define the `Capability` enum (`read`, `update`, `delete`, `add_child`, `move`, `copy`, `style`) in `domain/models.py`

## 3. DOCX Object Resolver

- [x] 3.1 Create `src/offagent/objects/docx_objects.py` implementing `ObjectResolver` for DOCX
- [x] 3.2 Implement `get_object` for: `document`, `section`, `paragraph`, `run`, `table`, `table_row`, `table_cell`, `image`, `page_break`
- [x] 3.3 Implement `list_children` for each container type with optional `child_type` filter
- [x] 3.4 Implement `resolve_capabilities` for each DOCX object type
- [x] 3.5 Add unit tests covering locator resolution and capability computation for DOCX object types

## 4. PPTX Object Resolver

- [x] 4.1 Create `src/offagent/objects/pptx_objects.py` implementing `ObjectResolver` for PPTX
- [x] 4.2 Implement `get_object` for: `presentation`, `slide`, `notes`, `shape`, `text_shape`, `image_shape`, `table`, `table_row`, `table_cell`, `group_shape`
- [x] 4.3 Implement `list_children` for each container type with optional `child_type` filter
- [x] 4.4 Implement `resolve_capabilities` for each PPTX object type
- [x] 4.5 Add unit tests covering locator resolution and capability computation for PPTX object types

## 5. XLSX Object Resolver

- [x] 5.1 Create `src/offagent/objects/xlsx_objects.py` implementing `ObjectResolver` for XLSX
- [x] 5.2 Implement `get_object` for: `workbook`, `worksheet`, `row`, `column`, `cell`, `range`, `table`, `merged_range`, `formula_cell`, `named_range`
- [x] 5.3 Implement `list_children` for each container type with optional `child_type` filter and `limit`
- [x] 5.4 Implement `resolve_capabilities` for each XLSX object type (including workbook-policy constraints such as single-sheet deletion guard)
- [x] 5.5 Add unit tests covering locator resolution and capability computation for XLSX object types

## 6. AppServices Object Methods (Phase 1 — Read)

- [x] 6.1 Add `get_object(document_id, locator) -> ObjectPayload` to `AppServices`, dispatching to the correct format resolver
- [x] 6.2 Add `list_children(document_id, locator, child_type, limit) -> list[ChildSummary]` to `AppServices`
- [x] 6.3 Integrate stale-locator detection (content hash check) into `get_object` and `list_children`

## 7. AppServices Object Methods (Phase 2 — Write)

- [x] 7.1 Add `create_object(document_id, parent_locator, object_type, properties, position, output_mode) -> MutationResult` to `AppServices`
- [x] 7.2 Add `update_object(document_id, locator, properties, output_mode) -> MutationResult` delegating to existing adapter write paths where applicable
- [x] 7.3 Add `move_object(document_id, locator, new_parent_locator, position, output_mode) -> MutationResult` to `AppServices`
- [x] 7.4 Add `copy_object(document_id, locator, target_parent_locator, position, output_mode) -> MutationResult` to `AppServices`
- [x] 7.5 Add `batch_edit(document_id, operations, output_mode, dry_run) -> BatchResult` to `AppServices` with in-memory atomicity

## 8. AppServices Object Methods (Phase 3 — Delete)

- [x] 8.1 Add `delete_object(document_id, locator, output_mode) -> MutationResult` to `AppServices`
- [x] 8.2 Enforce capability check before delete; raise `TargetNotEditableError` if `delete` not in capabilities

## 9. MCP Transport Models and Converters

- [x] 9.1 Add Pydantic request/response models for all V2 tools in `interfaces/mcp_models.py`
- [x] 9.2 Add converters in `interfaces/mcp_converters.py` for `ObjectPayload`, `ChildSummary`, `MutationResult`, `BatchResult`
- [x] 9.3 Update `search_objects` response model to include `locator`, `object_type`, `match_mode` fields

## 10. MCP Tool Registration (Phase 1 — Read)

- [x] 10.1 Add `_register_v2_tools(mcp, services)` function in `interfaces/mcp.py`
- [x] 10.2 Register `get_object` MCP tool
- [x] 10.3 Register `list_children` MCP tool
- [x] 10.4 Register `search_objects` as the canonical V2 search tool
- [x] 10.5 Register `search_documents` as a deprecated alias that strips `object_type` and `match_mode` from the response

## 11. MCP Tool Registration (Phase 2 — Write)

- [x] 11.1 Register `create_object` MCP tool
- [x] 11.2 Register `update_object` MCP tool
- [x] 11.3 Register `move_object` MCP tool
- [x] 11.4 Register `copy_object` MCP tool
- [x] 11.5 Register `batch_edit` MCP tool

## 12. MCP Tool Registration (Phase 3 — Delete + Escape Hatches)

- [x] 12.1 Register `delete_object` MCP tool
- [x] 12.2 Add `_register_escape_hatch_tools(mcp, services)` function in `interfaces/mcp.py`
- [x] 12.3 Register DOCX escape hatches: `docx_set_paragraph_style`, `docx_insert_page_break`, `docx_add_table`, `docx_merge_table_cells`
- [x] 12.4 Register PPTX escape hatches: `pptx_add_slide`, `pptx_duplicate_slide`, `pptx_set_slide_layout`, `pptx_add_text_shape`
- [x] 12.5 Register XLSX escape hatches: `xlsx_write_range`, `xlsx_insert_rows`, `xlsx_insert_columns`, `xlsx_set_formula`, `xlsx_merge_cells`

## 13. DOCX Escape Hatch Implementations

- [x] 13.1 Implement `docx_set_paragraph_style` in `docx_objects.py` with style catalog validation
- [x] 13.2 Implement `docx_insert_page_break` in `docx_objects.py`
- [x] 13.3 Implement `docx_add_table` in `docx_objects.py` with optional column widths and style name
- [x] 13.4 Implement `docx_merge_table_cells` in `docx_objects.py` with rectangular range validation

## 14. PPTX Escape Hatch Implementations

- [x] 14.1 Implement `pptx_add_slide` in `pptx_objects.py` with layout index/name validation
- [x] 14.2 Implement `pptx_duplicate_slide` in `pptx_objects.py`
- [x] 14.3 Implement `pptx_set_slide_layout` in `pptx_objects.py`
- [x] 14.4 Implement `pptx_add_text_shape` in `pptx_objects.py` with position and size parameters

## 15. XLSX Escape Hatch Implementations

- [x] 15.1 Implement `xlsx_write_range` in `xlsx_objects.py` with dimension validation
- [x] 15.2 Implement `xlsx_insert_rows` in `xlsx_objects.py`
- [x] 15.3 Implement `xlsx_insert_columns` in `xlsx_objects.py`
- [x] 15.4 Implement `xlsx_set_formula` in `xlsx_objects.py` with formula format validation
- [x] 15.5 Implement `xlsx_merge_cells` in `xlsx_objects.py` with overlap detection

## 16. Integration Tests

- [x] 16.1 Add MCP integration tests for `get_object` and `list_children` across DOCX, PPTX, XLSX fixtures
- [x] 16.2 Add MCP integration tests for `create_object`, `update_object`, `delete_object` across all three formats
- [x] 16.3 Add MCP integration tests for `move_object` and `copy_object`
- [x] 16.4 Add MCP integration test for `batch_edit` including atomic failure case and dry_run mode
- [x] 16.5 Add MCP integration test for `search_objects` verifying that returned locators are usable in `get_object`
- [x] 16.6 Add MCP integration test for the `search_documents` alias verifying the pre-V2 response shape
- [x] 16.7 Add MCP integration tests for all DOCX, PPTX, and XLSX escape hatch tools
