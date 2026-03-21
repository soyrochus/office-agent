## Purpose

Define the cli-output-modes capability for Office Agent.

## Requirements

### Requirement: JSON output mode for structured commands
The system SHALL support a `--json` output mode on every CLI command that returns structured data, and the emitted payload SHALL be valid JSON without extra human-readable lines. Search result payloads SHALL include `match_mode` and `scores` fields on every hit object, using `null` when a retrieval mode does not populate them. Commands that can otherwise render live progress SHALL suppress that progress feedback when `--json` is requested.

#### Scenario: Search returns machine-readable JSON
- **WHEN** a user runs a structured command such as `office-agent search ... --json`
- **THEN** the command writes valid JSON representing the command result, includes `match_mode` and `scores` on each hit object, and no extra prose to stdout

#### Scenario: Index returns machine-readable JSON without progress noise
- **WHEN** a user runs `office-agent index <path> --json`
- **THEN** the command writes a valid JSON indexing result and emits no transient progress feedback

### Requirement: Quiet output mode
The system SHALL support a `--quiet` output mode on all CLI commands that suppress informational success output and transient progress feedback while still emitting error output when a command fails.

#### Scenario: Quiet success suppresses informational lines
- **WHEN** a user runs a successful command with `--quiet`
- **THEN** the command does not emit normal success narration, human-readable result summaries, or transient progress feedback

### Requirement: Consistent default human-readable formatting
The system SHALL use a consistent human-readable output format across CLI commands when neither `--json` nor `--quiet` is requested. Search results SHALL display retrieval-mode metadata and any available score breakdown without falling back to ad hoc formatting.

#### Scenario: Default output follows shared formatting conventions
- **WHEN** a user runs supported commands in the default output mode
- **THEN** the commands render their results using a shared formatting style instead of ad hoc per-command string layouts

#### Scenario: Search shows mode-aware formatting
- **WHEN** a user runs `office-agent search` in semantic or hybrid mode in the default output mode
- **THEN** each rendered hit includes its match mode and any available component scores using the shared formatting conventions
