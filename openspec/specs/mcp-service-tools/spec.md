## Purpose

Define the MCP tool contract that exposes Office Agent document workflows over the shared service layer.

## Requirements

### Requirement: Document management tools
The system SHALL expose MCP tools for `index_documents`, `refresh_document`, and `list_documents` that return structured document-management results rather than human-formatted CLI output.

#### Scenario: Client indexes documents through MCP
- **WHEN** an MCP client calls `index_documents` with one or more document paths
- **THEN** the server returns a structured indexing result describing the documents scanned, indexed, and skipped

### Requirement: Search, locate, and read tools
The system SHALL expose MCP tools for `search_documents`, `locate_item`, and `read_item` that preserve the same document-query behavior as the shared application service layer. `search_documents` SHALL accept an optional `mode` parameter with values `keyword`, `semantic`, or `hybrid`, defaulting to `keyword`.

#### Scenario: Client searches and reads indexed content
- **WHEN** an MCP client indexes a fixture document and then calls `search_documents`, `locate_item`, and `read_item` with matching inputs
- **THEN** the server returns the same hit, locator, and content data that the equivalent application-service workflow would produce

#### Scenario: Client selects retrieval mode
- **WHEN** an MCP client calls `search_documents` with `mode="semantic"` or `mode="hybrid"`
- **THEN** the server executes the corresponding retrieval mode and returns mode-aware search hits from the shared service layer

### Requirement: Write tools
The system SHALL expose MCP tools for `replace_text`, `append_text`, and `write_cell` that apply the existing write semantics, including versioned output defaults and format-specific behavior.

#### Scenario: Client performs an edit through MCP
- **WHEN** an MCP client calls a supported write tool against an indexed document item
- **THEN** the server returns a structured write result that identifies the updated item and the output document path produced by the write

### Requirement: Shared schemas for tool inputs and outputs
The system SHALL define explicit machine-readable schemas for each MCP tool input and output so MCP clients can validate arguments and parse structured responses consistently. Those schemas SHALL remain aligned with the defined Pydantic transport models and acceptance assertions used by the MCP integration suite. The `search_documents` schema SHALL include the optional `mode` input, and search hit responses SHALL expose retrieval metadata and score fields consistent with the shared transport model.

#### Scenario: Client inspects tool schemas
- **WHEN** an MCP client requests the tool definitions for the Office Agent MCP server
- **THEN** each tool definition includes a concrete input schema and returns data matching its documented response shape

#### Scenario: Acceptance suite validates schema alignment
- **WHEN** the MCP integration suite inspects the Office Agent tool definitions
- **THEN** the reported tool schemas match the transport-model contract used by the implementation and tests

#### Scenario: Search schema exposes retrieval metadata
- **WHEN** an MCP client inspects or invokes `search_documents`
- **THEN** the tool schema advertises the optional `mode` argument and each returned hit exposes `match_mode` and `scores` consistent with the transport model

### Requirement: Cross-format tool parity
The system SHALL support the MCP tool workflows for DOCX, PPTX, and XLSX wherever the corresponding shared service operation already supports those file types. The acceptance suite SHALL verify the documented index, search, locate, read, and supported write cycle against the golden fixture corpus.

#### Scenario: Client completes the workflow against the fixture corpus
- **WHEN** an MCP client performs an index, search, locate, read, and supported write cycle across the fixture DOCX, PPTX, and XLSX documents
- **THEN** each MCP tool call succeeds or fails with the same format-specific semantics as the shared application services
