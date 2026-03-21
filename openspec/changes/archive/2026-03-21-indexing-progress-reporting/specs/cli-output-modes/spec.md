## MODIFIED Requirements

### Requirement: JSON output mode for structured commands
The system SHALL support a `--json` output mode on every CLI command that returns structured data, and the emitted payload SHALL be valid JSON without extra human-readable lines. Commands that can otherwise render live progress SHALL suppress that progress feedback when `--json` is requested.

#### Scenario: Search returns machine-readable JSON
- **WHEN** a user runs a structured command such as `office-agent search ... --json`
- **THEN** the command writes valid JSON representing the command result and no extra prose to stdout

#### Scenario: Index returns machine-readable JSON without progress noise
- **WHEN** a user runs `office-agent index <path> --json`
- **THEN** the command writes a valid JSON indexing result and emits no transient progress feedback

### Requirement: Quiet output mode
The system SHALL support a `--quiet` output mode on all CLI commands that suppress informational success output and transient progress feedback while still emitting error output when a command fails.

#### Scenario: Quiet success suppresses informational lines
- **WHEN** a user runs a successful command with `--quiet`
- **THEN** the command does not emit normal success narration, human-readable result summaries, or transient progress feedback
