## Purpose

Define the acceptance-test-coverage capability for Office Agent.

## Requirements


### Requirement: CLI acceptance coverage
The system SHALL include CLI acceptance coverage for `index`, `reindex`, `search`, `locate`, `read`, `replace`, `append`, `write-cell`, `list`, `show`, and `doctor` against the golden fixture corpus.

#### Scenario: CLI acceptance suite exercises the command surface
- **WHEN** the CLI acceptance suite runs
- **THEN** it verifies the full supported command surface against the version-controlled Office fixture corpus

### Requirement: CLI exit-code and output-mode assertions
The system SHALL verify CLI exit codes and output-mode behavior for success, not-found, not-editable, policy-refused, JSON, and quiet workflows.

#### Scenario: Acceptance suite validates CLI contract
- **WHEN** the CLI acceptance suite exercises failure and formatting scenarios
- **THEN** it asserts the documented exit codes and output behavior rather than only business results

### Requirement: MCP acceptance coverage
The system SHALL include MCP integration coverage that starts the stdio server, invokes all nine required tools, validates tool schemas, and verifies the documented result structures against the golden fixture corpus.

#### Scenario: MCP acceptance suite validates full tool coverage
- **WHEN** the MCP acceptance suite runs against the Office Agent MCP server
- **THEN** it confirms that each required tool can be discovered and exercised with the documented schema and result contract
