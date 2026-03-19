## Purpose

Define the security-path-guards capability for Office Agent.

## Requirements


### Requirement: Normalized path validation
The system SHALL normalize document and output paths, including symlink resolution and `..` traversal cleanup, before applying any policy checks or file operations.

#### Scenario: Policy checks use resolved paths
- **WHEN** a user supplies a path containing symlinks or traversal components
- **THEN** the application evaluates policy enforcement against the fully resolved canonical path

### Requirement: Allowed-root enforcement for reads
The system SHALL reject read-oriented operations when the target document path falls outside the configured allowed roots.

#### Scenario: Read outside allowed roots is refused
- **WHEN** a user attempts to index, show, locate, or read a document outside the configured allowed roots
- **THEN** the operation fails with a policy-refused error instead of reading that document

### Requirement: Output-root enforcement for writes
The system SHALL reject write operations when the resolved output path falls outside the configured allowed output roots.

#### Scenario: Write outside allowed output roots is refused
- **WHEN** a write workflow resolves an output path outside the configured output roots
- **THEN** the operation fails with a policy-refused error instead of writing the file

### Requirement: Non-destructive and non-executable document handling
The system SHALL not delete files, execute macros, process embedded objects, or dereference external links as part of any Office document workflow.

#### Scenario: Document processing remains non-destructive
- **WHEN** the application indexes, reads, or writes supported Office documents
- **THEN** it performs only the explicit supported operations and does not delete files or execute embedded document behaviors
