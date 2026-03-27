## 1. Semantic Models And Shared Contracts

- [ ] 1.1 Add semantic domain models for structure units, slide bundles, DOCX blocks, sheet snapshots, and structured write results in `src/offagent/domain/models.py` or adjacent shared model modules
- [ ] 1.2 Add MCP request and response models for the new semantic read and write tools in `src/offagent/interfaces/mcp_models.py`
- [ ] 1.3 Add shared conversion helpers so semantic service results map cleanly into MCP transport models without overloading `ItemRef`

## 2. Adapter Semantic Extraction And Write Helpers

- [ ] 2.1 Extend `src/offagent/adapters/docx_adapter.py` with ordered block traversal, paragraph and table extraction helpers, and paragraph-oriented semantic write helpers
- [ ] 2.2 Extend `src/offagent/adapters/pptx_adapter.py` with presentation structure, slide bundle, and slide notes helpers that preserve slide and shape order
- [ ] 2.3 Extend `src/offagent/adapters/xlsx_adapter.py` with workbook structure, sheet snapshot, row append, and table write helpers that preserve worksheet ordering and coordinates
- [ ] 2.4 Add focused adapter tests covering DOCX block ordering, PPTX notes and bundle extraction, and XLSX snapshot and structured write behavior

## 3. AppServices Semantic Operations

- [ ] 3.1 Add semantic read entrypoints to `src/offagent/app/services.py` for document structure, presentation structure, slide bundles, workbook structure, sheet snapshots, and DOCX block retrieval
- [ ] 3.2 Add structured write entrypoints to `src/offagent/app/services.py` for `append_row`, `write_table`, `append_paragraph`, and `replace_block` using existing path-policy and output-mode handling
- [ ] 3.3 Ensure semantic operations resolve documents through indexed `document_id` lookups and return explicit errors for unsupported file-type or target combinations
- [ ] 3.4 Add service-level tests covering cross-format structure reads, DOCX paragraph-only block replacement, and structured write result shapes

## 4. MCP Tool Registration And Schema Exposure

- [ ] 4.1 Register the semantic inspection tools in `src/offagent/interfaces/mcp.py`: `get_document_structure`, `get_presentation_structure`, `get_slide_bundle`, `get_slide_notes`, `get_workbook_structure`, `get_sheet_snapshot`, `get_document_blocks`, `get_paragraphs`, `get_tables`, and `get_block_bundle`
- [ ] 4.2 Register the semantic write tools in `src/offagent/interfaces/mcp.py`: `append_row`, `write_table`, `append_paragraph`, and `replace_block`
- [ ] 4.3 Extend MCP error handling and tool descriptions so semantic tools expose the documented structured schemas and format-specific failures consistently
- [ ] 4.4 Add MCP integration tests covering semantic structure inspection and supported structured writes across DOCX, PPTX, and XLSX fixtures

## 5. End-To-End Verification

- [ ] 5.1 Add acceptance coverage that exercises the semantic MCP workflows against the golden Office fixture corpus
- [ ] 5.2 Verify the new semantic tool schemas match the Pydantic transport contracts and remain discoverable through MCP tool introspection
- [ ] 5.3 Run the relevant adapter, service, MCP, and acceptance tests for structured document support and fix any contract mismatches
