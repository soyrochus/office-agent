## ADDED Requirements

### Requirement: JSON output mode for structured commands
The system SHALL support a `--json` output mode on every CLI command that returns structured data, and the emitted payload SHALL be valid JSON without extra human-readable lines.

#### Scenario: Search returns machine-readable JSON
- **WHEN** a user runs a structured command such as `office-agent search ... --json`
- **THEN** the command writes valid JSON representing the command result and no extra prose to stdout

### Requirement: Quiet output mode
The system SHALL support a `--quiet` output mode on all CLI commands that suppresses informational success output while still emitting error output when a command fails.

#### Scenario: Quiet success suppresses informational lines
- **WHEN** a user runs a successful command with `--quiet`
- **THEN** the command does not emit normal success narration or human-readable result summaries to stdout

### Requirement: Consistent default human-readable formatting
The system SHALL use a consistent human-readable output format across CLI commands when neither `--json` nor `--quiet` is requested.

#### Scenario: Default output follows shared formatting conventions
- **WHEN** a user runs supported commands in the default output mode
- **THEN** the commands render their results using a shared formatting style instead of ad hoc per-command string layouts
