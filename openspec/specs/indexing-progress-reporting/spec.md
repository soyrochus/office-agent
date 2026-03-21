## Purpose

Define interactive indexing progress behavior for Office Agent.

## Requirements

### Requirement: Interactive indexing progress
The system SHALL report progress for `office-agent index` and `office-agent reindex` across the full indexing run when stderr is attached to an interactive terminal and progress output is not otherwise suppressed. The progress display SHALL include the current file position and the total file count for the active run.

#### Scenario: Index command reports file progress
- **WHEN** a user runs `office-agent index <path>` in an interactive terminal without `--quiet` or `--json`
- **THEN** the command renders incremental progress for the indexing run, including the current file position and total files being processed

#### Scenario: Reindex command reports file progress
- **WHEN** a user runs `office-agent reindex <path>` in an interactive terminal without `--quiet` or `--json`
- **THEN** the command renders the same progress feedback conventions as `office-agent index`

### Requirement: Embedding item progress
The system SHALL report per-item embedding progress for a file when indexing is run with embedding generation enabled and the file produces one or more indexed items.

#### Scenario: Embedding generation advances item progress
- **WHEN** a file is indexed with embeddings enabled and it yields one or more indexed items
- **THEN** the progress reporting for that file includes completed-item updates from the first embedding through the final embedding

#### Scenario: Files without embedding work omit embedding progress
- **WHEN** embeddings are disabled or the current file yields no indexed items
- **THEN** the command does not render an embedding progress sub-task for that file

### Requirement: Reporter lifecycle contract for indexing services
The shared indexing services SHALL expose progress lifecycle events through an optional reporter contract that callers can provide without coupling the services to terminal rendering libraries.

#### Scenario: Caller receives indexing lifecycle events
- **WHEN** a caller invokes the indexing workflow with a reporter implementation
- **THEN** the service emits overall-start, per-file start, optional embedding progress, per-file completion, and overall-completion events in execution order for the work performed

#### Scenario: Null reporter preserves indexing behavior
- **WHEN** a caller invokes the indexing workflow without providing a reporter
- **THEN** indexing completes with the same persisted results and without requiring a terminal rendering dependency

### Requirement: Non-interactive runs suppress live progress
The system SHALL suppress live progress rendering when stderr is not attached to an interactive terminal, while still completing indexing and emitting the normal final command result.

#### Scenario: Redirected stderr disables progress rendering
- **WHEN** a user runs `office-agent index` or `office-agent reindex` with stderr redirected or otherwise non-interactive
- **THEN** the command completes without rendering live progress updates
