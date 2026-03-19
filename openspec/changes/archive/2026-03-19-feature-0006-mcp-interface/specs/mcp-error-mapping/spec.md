## ADDED Requirements

### Requirement: Structured MCP errors for expected failures
The system SHALL translate expected service-layer failures into structured MCP error responses with descriptive messages instead of exposing raw Python exceptions or CLI exit semantics.

#### Scenario: Client triggers a user-correctable service failure
- **WHEN** an MCP client calls a tool with an invalid locator, missing document, or unsupported argument combination
- **THEN** the server returns a structured MCP error describing the failure condition

### Requirement: Stale locator error preservation
The system SHALL preserve stale-locator failures as distinct MCP error responses so clients can distinguish source-drift protection from other write errors.

#### Scenario: Client writes against a stale indexed target
- **WHEN** an MCP client invokes a write tool after the indexed source document has changed and the original target can no longer be resolved safely
- **THEN** the server returns an MCP error that identifies the failure as a stale-locator condition

### Requirement: Stable error behavior for integration clients
The system SHALL return stable, repeatable error response shapes for the documented tool surface so automated MCP clients and integration tests can assert failure semantics reliably.

#### Scenario: Integration test validates an error response
- **WHEN** the MCP integration harness invokes a tool in a known failure condition
- **THEN** the server returns an error response with a predictable structure and descriptive message suitable for automated assertions
