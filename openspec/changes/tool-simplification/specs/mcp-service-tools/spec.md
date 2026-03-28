## MODIFIED Requirements

### Requirement: Search, locate, and read tools
The system SHALL expose MCP tools for `search_documents` and `get_node`. `search_documents` SHALL accept an optional `mode` parameter with values `keyword`, `semantic`, or `hybrid`, defaulting to `keyword`. Every `locator` field in a `search_documents` response SHALL be directly usable as the `node_id` argument to `get_node` and `write_node` without transformation. The tools `locate_item` and `read_item` SHALL NOT be registered on the MCP surface.

#### Scenario: Client searches indexed content and reads a hit
- **WHEN** an MCP client indexes a fixture document, calls `search_documents`, and then passes a hit `locator` to `get_node`
- **THEN** `search_documents` returns hits with `locator`, `preview`, and `score` fields, and `get_node` returns the current node content for the same locator without error

#### Scenario: Client selects retrieval mode
- **WHEN** an MCP client calls `search_documents` with `mode="semantic"` or `mode="hybrid"`
- **THEN** the server executes the corresponding retrieval mode and returns mode-aware search hits from the shared service layer

### Requirement: Semantic document tools
The system SHALL expose MCP tools for `get_structure` and `get_section` as the unified structural navigation layer. The tools `get_document_structure`, `get_document_blocks`, `get_paragraphs`, `get_presentation_structure`, `get_slide_bundle`, `get_slide_notes`, `get_workbook_structure`, `get_sheet_snapshot`, and `get_block_bundle` SHALL NOT be registered on the MCP surface. `get_structure` and `get_section` SHALL return structured results from the shared service layer, with format-specific payloads determined by the document's `file_type`.

#### Scenario: Client inspects structured Office content through unified tools
- **WHEN** an MCP client calls `get_structure` for an indexed Office document
- **THEN** the server returns a section list appropriate for the document format, with each section carrying a `locator` valid for `get_section`

#### Scenario: Client drills into a section
- **WHEN** an MCP client calls `get_section` with a locator from `get_structure`
- **THEN** the server returns the full format-specific payload for that section

### Requirement: Write tools
The system SHALL expose MCP tools for `write_node`, `insert_content`, `xlsx_insert_rows`, and `docx_get_tables` for mutation and format-specific extraction operations. The tools `replace_text`, `append_text`, `write_cell`, `append_row`, `write_table`, `append_paragraph`, and `replace_block` SHALL NOT be registered on the MCP surface. All write tools SHALL default to `output_mode="versioned"` and SHALL re-index the output document before returning.

#### Scenario: Client performs a write through MCP
- **WHEN** an MCP client calls `write_node` against a supported indexed document item
- **THEN** the server returns a structured write result that identifies the updated item, the previous text, and the output document path

#### Scenario: Client appends rows to an XLSX worksheet
- **WHEN** an MCP client calls `xlsx_insert_rows` against an indexed XLSX document
- **THEN** the server returns a structured result identifying the number of rows inserted and the first row locator

### Requirement: Shared schemas for tool inputs and outputs
The system SHALL define explicit machine-readable schemas for each of the 11 MCP tools and their inputs and outputs so MCP clients can validate arguments and parse structured responses consistently. Those schemas SHALL remain aligned with the defined Pydantic transport models and acceptance assertions used by the MCP integration suite. The schemas for the unified structural tools (`get_structure`, `get_section`) and unified write tools (`write_node`, `insert_content`, `xlsx_insert_rows`, `docx_get_tables`) SHALL advertise their structured request fields and response shapes.

#### Scenario: Client inspects tool schemas
- **WHEN** an MCP client requests the tool definitions for the Office Agent MCP server
- **THEN** exactly 11 tool definitions are returned and each includes a concrete input schema and returns data matching its documented response shape

#### Scenario: Acceptance suite validates schema alignment
- **WHEN** the MCP integration suite inspects the Office Agent tool definitions
- **THEN** the reported tool schemas match the transport-model contract used by the implementation and tests

### Requirement: Cross-format tool parity
The system SHALL support the MCP semantic document workflows for DOCX, PPTX, and XLSX wherever the corresponding shared service operation supports those file types. `get_structure`, `get_section`, `get_node`, and `write_node` SHALL operate across all three formats. Format-specific tools (`docx_get_tables`, `xlsx_insert_rows`, `insert_content`) SHALL fail explicitly, not silently, when called on an unsupported document type. The acceptance suite SHALL verify the index, structure inspection, and write cycles against the golden fixture corpus for all three formats using the unified tool surface.

#### Scenario: Client completes semantic MCP workflows across the fixture corpus
- **WHEN** an MCP client performs `get_structure`, `get_section`, `get_node`, and `write_node` workflows across fixture DOCX, PPTX, and XLSX documents
- **THEN** each MCP tool call succeeds with format-appropriate results and format-specific tools return explicit errors when called on unsupported formats

