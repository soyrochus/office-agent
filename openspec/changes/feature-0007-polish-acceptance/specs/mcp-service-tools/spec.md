## MODIFIED Requirements

### Requirement: Shared schemas for tool inputs and outputs
The system SHALL define explicit machine-readable schemas for each MCP tool input and output so MCP clients can validate arguments and parse structured responses consistently. Those schemas SHALL remain aligned with the defined Pydantic transport models and acceptance assertions used by the MCP integration suite.

#### Scenario: Client inspects tool schemas
- **WHEN** an MCP client requests the tool definitions for the Office Agent MCP server
- **THEN** each tool definition includes a concrete input schema and returns data matching its documented response shape

#### Scenario: Acceptance suite validates schema alignment
- **WHEN** the MCP integration suite inspects the Office Agent tool definitions
- **THEN** the reported tool schemas match the transport-model contract used by the implementation and tests

### Requirement: Cross-format tool parity
The system SHALL support the MCP tool workflows for DOCX, PPTX, and XLSX wherever the corresponding shared service operation already supports those file types. The acceptance suite SHALL verify the documented index, search, locate, read, and supported write cycle against the golden fixture corpus.

#### Scenario: Client completes the workflow against the fixture corpus
- **WHEN** an MCP client performs an index, search, locate, read, and supported write cycle across the fixture DOCX, PPTX, and XLSX documents
- **THEN** each MCP tool call succeeds or fails with the same format-specific semantics as the shared application services
