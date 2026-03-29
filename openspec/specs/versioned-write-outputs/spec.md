## Purpose

Define the versioned-write-outputs capability for Office Agent.
## Requirements
### Requirement: Versioned write outputs by default
The system SHALL write `replace`, `append`, and `write-cell` operations to versioned output files by default instead of overwriting the source document.

#### Scenario: A write produces a versioned sibling file
- **WHEN** a user performs a supported write operation without requesting in-place overwrite
- **THEN** the system saves the updated document to a new file rather than modifying the source document path

### Requirement: Versioned output naming
The system SHALL generate versioned filenames in the form `<name>.edited.<timestamp>.<ext>` using a sortable UTC timestamp.

#### Scenario: A generated output path uses the edited timestamp pattern
- **WHEN** the system determines the default output path for a write operation
- **THEN** the resulting filename contains `.edited.` followed by a UTC timestamp and preserves the source file extension

### Requirement: Configurable versioned output directory
The system SHALL support writing versioned outputs to a configured output directory and default to the source file directory when no output directory is configured.

#### Scenario: Config chooses the versioned output location
- **WHEN** an output directory is configured for the application
- **THEN** the generated versioned file is written under that directory instead of beside the source file

### Requirement: In-place overwrite is explicitly gated
The system SHALL permit in-place overwrite only when configuration explicitly allows it.

#### Scenario: In-place overwrite is rejected without opt-in
- **WHEN** a caller requests in-place overwrite and `allow_inplace_overwrite` is not enabled
- **THEN** the system fails the write operation instead of overwriting the source document

### Requirement: create_document follows the versioned-output convention
The system SHALL apply the same versioned-output path logic to `create_document` as it does to all other write operations.

#### Scenario: create_document with versioned mode produces a timestamped filename
- **WHEN** `create_document` is called with `output_mode="versioned"`
- **THEN** the written file path follows the `<name>.edited.<timestamp>.<ext>` convention, consistent with all other write operations

#### Scenario: create_document with in-place mode writes to the exact path
- **WHEN** `create_document` is called with `output_mode="inplace"` and `allow_inplace_overwrite` is enabled
- **THEN** the file is written to the exact caller-specified path without timestamp decoration

