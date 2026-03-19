## MODIFIED Requirements

### Requirement: CLI entrypoint wiring
The system SHALL expose an `office-agent` CLI entrypoint that initializes the application through the shared interface layer rather than embedding behavior directly in packaging metadata or shell scripts. That interface layer SHALL expose the full supported command surface, including `list`, `show`, and shared output-mode options needed for the final CLI contract.

#### Scenario: CLI command is available
- **WHEN** the package is installed in a Python environment
- **THEN** the `office-agent` command resolves to the Typer-based CLI application defined in the interface layer

#### Scenario: Final command surface is wired through the shared CLI app
- **WHEN** a user requests supported document-management commands such as `list`, `show`, `search`, or write workflows
- **THEN** the shared CLI application exposes those commands and their final output-mode options through one interface entrypoint
