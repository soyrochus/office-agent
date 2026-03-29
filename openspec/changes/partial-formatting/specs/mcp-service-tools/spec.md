## ADDED Requirements

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
