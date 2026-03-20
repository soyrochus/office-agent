## MODIFIED Requirements

### Requirement: Search, locate, and read tools
The system SHALL expose MCP tools for `search_documents`, `locate_item`, and `read_item` that preserve the same document-query behavior as the shared application service layer. `search_documents` SHALL accept an optional `mode` parameter with values `keyword`, `semantic`, or `hybrid`, defaulting to `keyword`.

#### Scenario: Client searches and reads indexed content
- **WHEN** an MCP client indexes a fixture document and then calls `search_documents`, `locate_item`, and `read_item` with matching inputs
- **THEN** the server returns the same hit, locator, and content data that the equivalent application-service workflow would produce

#### Scenario: Client selects retrieval mode
- **WHEN** an MCP client calls `search_documents` with `mode="semantic"` or `mode="hybrid"`
- **THEN** the server executes the corresponding retrieval mode and returns mode-aware search hits from the shared service layer

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
