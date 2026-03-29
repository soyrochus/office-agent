## Purpose

Define the MCP tool contract that exposes Office Agent document workflows over the shared service layer.
## Requirements
### Requirement: Document management tools
The system SHALL expose MCP tools for `index_documents`, `refresh_document`, and `list_documents` that return structured document-management results rather than human-formatted CLI output.

#### Scenario: Client indexes documents through MCP
- **WHEN** an MCP client calls `index_documents` with one or more document paths
- **THEN** the server returns a structured indexing result describing the documents scanned, indexed, and skipped

### Requirement: Search, locate, and read tools
The system SHALL expose MCP tools for `search_objects`, `locate_item`, and `read_item` that preserve the same document-query behavior as the shared application service layer. `search_objects` SHALL accept an optional `mode` parameter with values `keyword`, `semantic`, or `hybrid`, defaulting to `keyword`. Every search hit returned by `search_objects` SHALL include `document_id`, `locator`, `object_type`, `preview`, `score`, and `match_mode`. The `locator` field SHALL be directly usable in `get_object`, `update_object`, `delete_object`, `move_object`, and `copy_object`. The legacy tool name `search_documents` SHALL remain available as a deprecated alias that returns the pre-V2 hit shape (omitting `object_type` and `match_mode`) for backward compatibility.

#### Scenario: Client searches and reads indexed content
- **WHEN** an MCP client indexes a fixture document and then calls `search_objects`, `locate_item`, and `read_item` with matching inputs
- **THEN** the server returns the same hit, locator, and content data that the equivalent application-service workflow would produce

#### Scenario: Client selects retrieval mode
- **WHEN** an MCP client calls `search_objects` with `mode="semantic"` or `mode="hybrid"`
- **THEN** the server executes the corresponding retrieval mode and returns mode-aware search hits from the shared service layer

#### Scenario: Search hit locator is usable in object tools
- **WHEN** an MCP client calls `search_objects` and receives a hit with a `locator` field
- **THEN** calling `get_object` with that `document_id` and `locator` succeeds and returns a structured object payload

#### Scenario: Legacy alias returns pre-V2 shape
- **WHEN** an MCP client calls the deprecated `search_documents` tool
- **THEN** the server returns search hits without `object_type` and `match_mode` fields, preserving the pre-V2 response shape

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

### Requirement: Object mutation MCP tools accept partial-formatting inputs
The system SHALL expose the partial-formatting extensions for the existing object mutation tools over MCP without adding a new top-level tool.

#### Scenario: Client sends range-based inline styling through MCP
- **WHEN** an MCP client calls `style_inline` with a parent text object locator and a character range
- **THEN** the server validates the range-based payload and executes the shared service-layer partial-formatting workflow

#### Scenario: Client sends segment-based text mutation through MCP
- **WHEN** an MCP client calls `create_object` or `update_object` with structured text segments for a supported text-bearing object
- **THEN** the server validates the segment payload and dispatches the mutation through the shared service layer without requiring a separate MCP tool

### Requirement: MCP schemas advertise additive range and segment fields
The system SHALL publish machine-readable MCP schemas for the existing object mutation tools that include the additive partial-formatting inputs while preserving compatibility with legacy text-only payloads.

#### Scenario: Tool schema includes partial-formatting inputs
- **WHEN** an MCP client inspects the input schema for `create_object`, `update_object`, or `style_inline`
- **THEN** the schema advertises the supported range- and segment-based request fields alongside the existing plain-text inputs

#### Scenario: Unknown partial-formatting fields are rejected
- **WHEN** an MCP client sends unsupported range- or segment-related fields to an object mutation tool
- **THEN** the MCP validation layer rejects the request before any document mutation occurs

### Requirement: MCP partial-formatting behavior follows shared cross-format semantics
The system SHALL expose partial-formatting behavior over MCP with the same format-specific success and failure semantics as the shared application services.

#### Scenario: Supported text container succeeds over MCP
- **WHEN** an MCP client applies partial formatting to a supported DOCX, PPTX, or XLSX text container
- **THEN** the MCP response reflects the same successful mutation result, output path, and resolved locator semantics as the shared service layer

#### Scenario: Unsupported partial-formatting target fails over MCP
- **WHEN** an MCP client applies partial formatting to an unsupported target such as a non-text PPTX shape or unsupported XLSX cell type
- **THEN** the MCP server returns the same explicit validation or target error produced by the shared service layer

