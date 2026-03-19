## ADDED Requirements

### Requirement: SQLite store initialization
The system SHALL provide a SQLite-backed store that creates the foundational metadata and full-text schema on first use if the database does not already exist.

#### Scenario: Schema is created on first run
- **WHEN** the store opens against an empty database path
- **THEN** it creates the `documents`, `items`, and `items_fts` tables required for later indexing and search features

### Requirement: Reusable store connections
The system SHALL centralize database connection management in the indexing layer so application services and diagnostics use the same store setup behavior.

#### Scenario: Services use the same store setup path
- **WHEN** multiple application entrypoints need database access
- **THEN** they obtain connections through the shared store module rather than duplicating schema or connection logic

### Requirement: FTS5 capability validation
The system SHALL treat SQLite full-text support as part of the required runtime capability for the local index foundation.

#### Scenario: Full-text support is required
- **WHEN** the runtime environment does not support SQLite FTS5
- **THEN** the application can detect that condition and report the store as unavailable for the MVP foundation
