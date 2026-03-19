## Purpose

Define the write-reindex-synchronization capability for Office Agent.

## Requirements


### Requirement: Successful writes trigger automatic reindex
The system SHALL reindex the written output document after every successful `replace`, `append`, or `write-cell` operation.

#### Scenario: A write updates the index automatically
- **WHEN** a supported write operation completes successfully
- **THEN** the system indexes the written output document without requiring a separate manual reindex command

### Requirement: Search reflects the new written version
The system SHALL make newly written content discoverable through the local search index immediately after the automatic reindex completes.

#### Scenario: Search returns the updated output content
- **WHEN** a user searches for text introduced by a successful write
- **THEN** the search results include the newly written document version

### Requirement: Patch results identify the written output
The system SHALL return the path of the written output document as part of the write result so callers can distinguish versioned outputs from the original source file.

#### Scenario: Write response exposes the output path
- **WHEN** a write operation succeeds
- **THEN** the returned patch result identifies the output file path that was written and indexed

### Requirement: Versioned outputs remain separate indexed documents
The system SHALL index versioned outputs as their own document paths unless the write mode is explicitly in-place.

#### Scenario: Versioned output keeps the original source path distinct
- **WHEN** the default versioned write mode produces a new output file
- **THEN** the index contains the written version under its new path rather than rewriting the original source path in place
