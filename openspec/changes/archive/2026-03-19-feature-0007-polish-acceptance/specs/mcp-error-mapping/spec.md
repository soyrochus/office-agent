## MODIFIED Requirements

### Requirement: Structured MCP errors for expected failures
The system SHALL translate expected service-layer failures into structured MCP error responses with descriptive messages instead of exposing raw Python exceptions or CLI exit semantics. That behavior SHALL include not-found, not-editable, policy-refused, invalid-input, and stale-locator failures introduced by the final acceptance contract.

#### Scenario: Client triggers a user-correctable service failure
- **WHEN** an MCP client calls a tool with an invalid locator, missing document, or unsupported argument combination
- **THEN** the server returns a structured MCP error describing the failure condition

#### Scenario: Client triggers a policy-refused failure
- **WHEN** an MCP client invokes a read or write workflow that violates the configured path-guard policy
- **THEN** the server returns a structured MCP error describing the refusal instead of performing the operation

### Requirement: Stable error behavior for integration clients
The system SHALL return stable, repeatable error response shapes for the documented tool surface so automated MCP clients and integration tests can assert failure semantics reliably.

#### Scenario: Integration test validates an error response
- **WHEN** the MCP integration harness invokes a tool in a known failure condition
- **THEN** the server returns an error response with a predictable structure and descriptive message suitable for automated assertions
