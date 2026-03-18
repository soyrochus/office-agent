## ADDED Requirements

### Requirement: Configuration precedence
The system SHALL load configuration from built-in defaults, then optional file-based settings, then environment variable overrides, with later sources taking precedence over earlier ones.

#### Scenario: Environment overrides file settings
- **WHEN** a configuration value is defined in both the config file and the environment
- **THEN** the effective runtime configuration uses the environment value

### Requirement: Office document discovery
The system SHALL discover candidate Office documents by traversing configured roots and collecting metadata for files ending in `.docx`, `.pptx`, and `.xlsx`.

#### Scenario: Mixed directories are filtered to supported files
- **WHEN** discovery scans a directory containing Office files and unrelated files
- **THEN** the result includes only supported Office document paths with their modification metadata

### Requirement: Diagnostic command
The system SHALL expose `office-agent doctor` to report whether the runtime can import required libraries, access SQLite, write to the configured index location, and read configured document roots.

#### Scenario: Doctor reports environment checks
- **WHEN** a user runs `office-agent doctor`
- **THEN** the command emits pass/fail results for dependency imports, SQLite availability, index path writability, and document root readability

### Requirement: Diagnostic schema bootstrap
The system SHALL allow the diagnostic flow to verify index-store readiness without requiring prior indexing commands.

#### Scenario: Doctor can validate a new index path
- **WHEN** the configured database path does not yet exist and the location is writable
- **THEN** the diagnostic flow verifies that the foundational schema can be created successfully
