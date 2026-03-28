## ADDED Requirements

### Requirement: Semantic document tools
The system SHALL expose MCP tools for semantic document inspection, including `get_document_structure`, `get_presentation_structure`, `get_slide_bundle`, `get_slide_notes`, `get_workbook_structure`, `get_sheet_snapshot`, `get_document_blocks`, `get_paragraphs`, `get_tables`, and `get_block_bundle`. These tools SHALL return structured semantic results from the shared service layer rather than human-formatted output.

#### Scenario: Client inspects structured Office content through MCP
- **WHEN** an MCP client calls one of the semantic document inspection tools for an indexed Office document
- **THEN** the server returns the corresponding structured semantic result for that document and target scope

## MODIFIED Requirements

### Requirement: Write tools
The system SHALL expose MCP tools for `replace_text`, `append_text`, `write_cell`, `append_row`, `write_table`, `append_paragraph`, and `replace_block` that apply the existing or semantic write semantics, including versioned output defaults and format-specific behavior.

#### Scenario: Client performs an indexed edit through MCP
- **WHEN** an MCP client calls one of the existing indexed write tools against a supported indexed document item
- **THEN** the server returns a structured write result that identifies the updated item and the output document path produced by the write

#### Scenario: Client performs a structured semantic write through MCP
- **WHEN** an MCP client calls `append_row`, `write_table`, `append_paragraph`, or `replace_block` against a supported indexed Office document
- **THEN** the server returns a structured write result that identifies the logical target that changed and the output document path produced by the write

### Requirement: Shared schemas for tool inputs and outputs
The system SHALL define explicit machine-readable schemas for each MCP tool input and output so MCP clients can validate arguments and parse structured responses consistently. Those schemas SHALL remain aligned with the defined Pydantic transport models and acceptance assertions used by the MCP integration suite. The schemas for the semantic document tools SHALL advertise their structured request fields and response shapes, including nested structure, bundle, block, snapshot, and structured-write payloads.

#### Scenario: Client inspects tool schemas
- **WHEN** an MCP client requests the tool definitions for the Office Agent MCP server
- **THEN** each tool definition includes a concrete input schema and returns data matching its documented response shape

#### Scenario: Acceptance suite validates schema alignment
- **WHEN** the MCP integration suite inspects the Office Agent tool definitions
- **THEN** the reported tool schemas match the transport-model contract used by the implementation and tests

#### Scenario: Semantic schemas expose structured payloads
- **WHEN** an MCP client inspects or invokes one of the semantic document tools
- **THEN** the tool schema advertises the required semantic inputs and the response preserves the documented structured payload shape for that tool

### Requirement: Cross-format tool parity
The system SHALL support the MCP semantic document workflows for DOCX, PPTX, and XLSX wherever the corresponding shared service operation supports those file types. The acceptance suite SHALL verify the documented index, structure inspection, and supported semantic write cycles against the golden fixture corpus in addition to the existing low-level MCP workflow coverage.

#### Scenario: Client completes semantic MCP workflows across the fixture corpus
- **WHEN** an MCP client performs structure inspection and supported semantic write workflows across fixture DOCX, PPTX, and XLSX documents
- **THEN** each MCP semantic tool call succeeds or fails with the same format-specific semantics as the shared application services
