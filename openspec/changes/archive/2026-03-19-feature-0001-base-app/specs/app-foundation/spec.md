## ADDED Requirements

### Requirement: Shared package foundation
The system SHALL provide a Python package named `offagent` with modules for configuration, domain models, locator parsing, indexing, application services, and interface adapters so later CLI and MCP features can build on the same core.

#### Scenario: Package structure is present
- **WHEN** the project is installed or inspected from source
- **THEN** it exposes the `src/offagent/` package with `config.py`, `domain/models.py`, `domain/locators.py`, `indexing/store.py`, `app/services.py`, and `interfaces/cli.py`

### Requirement: CLI entrypoint wiring
The system SHALL expose an `office-agent` CLI entrypoint that initializes the application through the shared interface layer rather than embedding behavior directly in packaging metadata or shell scripts.

#### Scenario: CLI command is available
- **WHEN** the package is installed in a Python environment
- **THEN** the `office-agent` command resolves to the Typer-based CLI application defined in the interface layer

### Requirement: Foundational domain contracts
The system SHALL define stable shared models for document references, item references, search hits, and patch operations so indexing, search, and edit flows can exchange consistent identifiers and payloads.

#### Scenario: Domain models cover core identifiers
- **WHEN** application code imports the shared domain layer
- **THEN** it can construct `DocumentRef`, `ItemRef`, `SearchHit`, and `PatchOperation` objects without relying on format-specific document adapters

### Requirement: Locator parser stubs
The system SHALL include locator parsing stubs that accept future direct and search-derived locator shapes without performing full resolution or document mutation in this feature.

#### Scenario: Locator parsing remains non-destructive
- **WHEN** a caller invokes the locator parsing layer with supported placeholder input
- **THEN** the layer returns stubbed parse output or explicit not-yet-implemented behavior without reading document contents or changing files
