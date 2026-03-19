## ADDED Requirements

### Requirement: MCP server startup from the CLI
The system SHALL start an MCP server over stdio when the user runs `office-agent mcp` without requiring additional MVP-specific arguments.

#### Scenario: Launching the MCP server from the CLI
- **WHEN** a user runs `office-agent mcp`
- **THEN** the process starts an MCP stdio server instead of the interactive CLI command flow

### Requirement: MCP tool advertisement
The system SHALL advertise the Office Agent MCP tool surface during MCP initialization so compatible clients can discover the available operations before invoking them.

#### Scenario: Client lists available tools after initialization
- **WHEN** an MCP client connects to the stdio server and requests the tool list
- **THEN** the server returns the supported Office Agent tool definitions with their names and schemas

### Requirement: Shared application configuration for MCP startup
The system SHALL use the same configuration-loading behavior for `office-agent mcp` as for the existing CLI commands, including default config discovery and explicit config-path overrides.

#### Scenario: MCP startup honors the shared config source
- **WHEN** a user starts `office-agent mcp` with the same configuration path or environment-based settings used by other CLI commands
- **THEN** the MCP server uses those settings for index location, document roots, and write-policy behavior
