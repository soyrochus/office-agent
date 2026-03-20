## MODIFIED Requirements

### Requirement: Configuration precedence
The system SHALL load configuration from built-in defaults, then optional file-based settings, then environment variable overrides, with later sources taking precedence over earlier ones. The effective configuration SHALL include any allowed-root and output-root policy fields required for document access enforcement, as well as embedding-model, embedding-dimension, vector-candidate, and hybrid-weight settings required for vector search behavior.

#### Scenario: Environment overrides file settings
- **WHEN** a configuration value is defined in both the config file and the environment
- **THEN** the effective runtime configuration uses the environment value

#### Scenario: Path policy settings participate in the same precedence rules
- **WHEN** allowed-root or output-root policy values are defined through file or environment configuration
- **THEN** the effective runtime policy uses the same precedence rules as the rest of the configuration model

#### Scenario: Embedding search settings participate in the same precedence rules
- **WHEN** embedding or hybrid-search settings are defined through file or environment configuration
- **THEN** the effective runtime configuration applies the same precedence rules to those settings as it does to the rest of the configuration model

### Requirement: Diagnostic command
The system SHALL expose `office-agent doctor` to report whether the runtime can import required libraries, access SQLite, write to the configured index location, and read configured document roots. The diagnostic output SHALL also report whether the configured allowed-root and output-root policy locations are usable for the enforced path guards, whether the embedding provider can be imported, whether the configured embedding model can be loaded, and whether the embedding sidecar tables and metadata are usable.

#### Scenario: Doctor reports environment checks
- **WHEN** a user runs `office-agent doctor`
- **THEN** the command emits pass/fail results for dependency imports, SQLite availability, index path writability, and document root readability

#### Scenario: Doctor reports path-policy readiness
- **WHEN** allowed-root or output-root policies are configured
- **THEN** the diagnostic command reports whether those configured locations are readable or writable as required by the path-guard policy

#### Scenario: Doctor reports vector-search readiness
- **WHEN** vector search is configured or embeddings already exist in the local index
- **THEN** the diagnostic command reports whether the embedding provider imports, the configured embedding model loads, and the embedding tables and metadata are present and consistent

### Requirement: Diagnostic schema bootstrap
The system SHALL allow the diagnostic flow to verify index-store readiness, including vector-sidecar schema readiness, without requiring prior indexing commands.

#### Scenario: Doctor can validate a new index path
- **WHEN** the configured database path does not yet exist and the location is writable
- **THEN** the diagnostic flow verifies that the foundational schema and vector-sidecar schema can be created successfully
