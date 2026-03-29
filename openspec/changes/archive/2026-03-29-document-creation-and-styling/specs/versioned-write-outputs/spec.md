## ADDED Requirements

### Requirement: create_document follows the versioned-output convention
The system SHALL apply the same versioned-output path logic to `create_document` as it does to all other write operations.

#### Scenario: create_document with versioned mode produces a timestamped filename
- **WHEN** `create_document` is called with `output_mode="versioned"`
- **THEN** the written file path follows the `<name>.edited.<timestamp>.<ext>` convention, consistent with all other write operations

#### Scenario: create_document with in-place mode writes to the exact path
- **WHEN** `create_document` is called with `output_mode="inplace"` and `allow_inplace_overwrite` is enabled
- **THEN** the file is written to the exact caller-specified path without timestamp decoration
