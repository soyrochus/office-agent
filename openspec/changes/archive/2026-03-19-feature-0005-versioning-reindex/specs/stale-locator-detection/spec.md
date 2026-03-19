## ADDED Requirements

### Requirement: Writes validate indexed content hashes
The system SHALL compare the indexed document `content_hash` with the current source file content before applying a write operation.

#### Scenario: A write checks the current source content before patching
- **WHEN** a user invokes `replace`, `append`, or `write-cell` for an indexed document
- **THEN** the system validates that the current source file content matches the indexed content hash before applying the patch

### Requirement: Deterministic target re-resolution on source drift
The system SHALL attempt to re-resolve the same item identifier against the current source content when the indexed content hash no longer matches the source file.

#### Scenario: A still-valid target is re-resolved after external changes
- **WHEN** the source file content has changed externally but the original item id still exists in the current document
- **THEN** the system re-resolves that item id and continues the write safely

### Requirement: Stale locator failures are explicit
The system SHALL fail with a stale-locator error when the indexed content hash has changed and the original target item can no longer be resolved safely.

#### Scenario: A disappeared target fails with stale-locator
- **WHEN** the source file changed externally and the original target item id no longer exists in the current content
- **THEN** the system aborts the write with a stale-locator failure instead of patching a different target

### Requirement: Stale locator failures use a dedicated CLI exit code
The system SHALL surface stale-locator failures through the CLI with exit code `3`.

#### Scenario: CLI reports stale-locator with the dedicated exit code
- **WHEN** a stale-locator failure occurs during a CLI write command
- **THEN** the CLI exits with code `3` and reports the stale-locator error to the user
