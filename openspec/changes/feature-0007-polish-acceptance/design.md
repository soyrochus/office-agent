## Context

The product already supports the core DOCX, PPTX, XLSX, versioned-write, and FastMCP workflows, but the user-facing contract is still incomplete. The CLI in [cli.py](/home/iwk/src/office-agent/src/offagent/interfaces/cli.py) currently exposes only the original command set, formats results directly with `typer.echo`, and maps most failures into a narrow `0/1/3` exit-code model. Configuration in [config.py](/home/iwk/src/office-agent/src/offagent/config.py) currently covers index and write-output settings but does not enforce allowed-root policy for reads and writes. Test coverage is also still shaped around generated temporary fixtures in [conftest.py](/home/iwk/src/office-agent/tests/conftest.py) rather than a version-controlled golden corpus and dedicated acceptance-style CLI directories.

This change is cross-cutting because it affects interface behavior, configuration, service-layer path validation, fixture strategy, and test layout at the same time. It also tightens the acceptance contract for the newer MCP surface in [mcp.py](/home/iwk/src/office-agent/src/offagent/interfaces/mcp.py), because final verification now depends on equivalent workflows and schema expectations across both CLI and MCP.

Constraints:
- Existing business logic should remain centralized in `AppServices`; CLI and MCP should not fork document workflow rules.
- The final exit-code matrix must distinguish invalid arguments, not-found targets, not-editable targets, and policy-refused writes instead of flattening them into one generic failure code.
- Path guard enforcement must normalize symlinks and traversal before any read or write is attempted.
- The fixture corpus must become deterministic and version-controlled instead of being synthesized implicitly for every test.
- CLI and MCP acceptance coverage must stay maintainable even as the command and tool surface expands.

## Goals / Non-Goals

**Goals:**
- Add the missing CLI summary commands and establish a consistent output layer that can render human-readable, JSON, and quiet modes from the same underlying results.
- Extend configuration and service-layer validation to enforce allowed-root and output-root security guards before document operations execute.
- Establish deterministic golden fixtures under `tests/fixtures/` and refactor acceptance-oriented tests to use them consistently.
- Enforce the complete exit-code matrix across all CLI commands.
- Expand CLI and MCP tests so the final product contract is verified end to end rather than only through feature-by-feature unit and service tests.

**Non-Goals:**
- Replacing the current Typer-based CLI framework.
- Adding HTTP APIs, benchmarking infrastructure, or semantic search.
- Introducing file deletion, cleanup, or lifecycle management for generated outputs.
- Expanding the MCP surface beyond the existing nine tools in this change.
- Solving multi-user coordination or locking concerns.

## Decisions

### 1. Add a CLI presentation layer instead of keeping command-specific `typer.echo` formatting inline

Decision:
Introduce a small CLI presentation layer that can render shared result models in three modes: human-readable default output, JSON output, and quiet output. Commands should gather structured results first, then hand them to a formatter instead of assembling strings inline.

Rationale:
The current CLI module mixes workflow invocation and presentation in each command. That becomes brittle once `--json`, `--quiet`, `list`, and `show` need to behave consistently across multiple result types. A narrow formatting layer reduces duplication without moving business logic out of services.

Alternatives considered:
- Keep formatting inline and add `if json/quiet` branches to every command.
  Rejected because it would scatter output policy through the whole CLI and make consistency hard to enforce.
- Move all formatting into the service layer.
  Rejected because rendering mode is an interface concern, not application business logic.

### 2. Add typed summary/read models for CLI and MCP consumption rather than special-casing `list` and `show`

Decision:
Extend the service boundary with structured document-summary and item-detail results that both `office-agent list/show` and future MCP-facing verification can consume.

Rationale:
`list` needs document metadata plus item counts, and `show` needs document and item summaries that are not currently exposed directly by `AppServices`. Adding explicit service results is cleaner than having CLI commands query the SQLite store directly and assemble their own ad hoc payloads.

Alternatives considered:
- Query the store directly in CLI-only code for `list` and `show`.
  Rejected because it would bypass the shared service boundary and create a second read path to maintain.
- Reuse only existing `DocumentRef` and `ItemRef` types.
  Rejected because those types do not currently capture item counts or richer document summaries cleanly.

### 3. Normalize path policy in the service/config layer before command or tool execution

Decision:
Add `allowed_roots` plus any explicit output-root policy to `AppConfig`, and centralize normalized path validation in shared helpers used by CLI and MCP workflows before indexing, reading, or writing documents.

Rationale:
The new security requirements are cross-interface. If path policy lives only in CLI parsing, MCP remains under-protected; if it lives only in adapters, validation happens too late. The service/config layer is the narrowest shared place to enforce resolution, symlink handling, and refusal semantics.

Alternatives considered:
- Enforce allowed-root checks only in the CLI.
  Rejected because MCP and any future interfaces would bypass the same policy.
- Enforce checks only during writes.
  Rejected because the feature scope also requires guarded reads.

### 4. Introduce dedicated exception classes for CLI exit-code mapping

Decision:
Add specific error types for invalid arguments, target-not-found, target-not-editable, and policy-refused operations, then update the CLI wrapper to map those exceptions deterministically to exit codes `2`, `3`, `4`, and `5`.

Rationale:
The current `_run_command` logic in `cli.py` groups most failures into exit code `1`, which is too coarse for the acceptance contract. Dedicated exception classes let the service and interface layers express meaning clearly without fragile string matching in the CLI.

Alternatives considered:
- Infer exit codes by matching error-message text.
  Rejected because message-based routing is brittle and hard to maintain.
- Return exit codes from service methods directly.
  Rejected because exit codes are CLI interface behavior, not service-layer domain behavior.

### 5. Move from generated ad hoc fixtures to a checked-in golden corpus while keeping targeted unit fixtures when useful

Decision:
Add canonical fixture documents under `tests/fixtures/` for acceptance and round-trip tests, and use those files for CLI and MCP suites. Keep lightweight generated fixtures only where unit-level tests benefit from highly specific synthetic inputs.

Rationale:
The current `conftest.py` generates small documents per test run, which is fine for focused service tests but does not satisfy the acceptance requirement for deterministic, version-controlled corpus files. A checked-in fixture corpus makes CLI and MCP workflows reproducible and easier to review.

Alternatives considered:
- Replace every existing generated fixture with checked-in files immediately.
  Rejected because some low-level tests still benefit from isolated generated inputs.
- Keep generating acceptance fixtures in setup code.
  Rejected because the scope explicitly requires deterministic version-controlled artifacts.

### 6. Split acceptance tests by interface while sharing common helper setup

Decision:
Create dedicated acceptance-oriented test groupings for CLI and MCP, likely under `tests/cli/` and `tests/mcp/`, while sharing common fixture-path and process helpers rather than duplicating setup logic across both interfaces.

Rationale:
The feature brief calls for fuller command and tool coverage than the current flat test files provide. Separating interface-level suites improves readability and mirrors the acceptance criteria, but common helper code still belongs in one place to avoid drift.

Alternatives considered:
- Keep appending more cases to the existing flat `tests/test_*` files.
  Rejected because the acceptance matrix is getting large enough to make the current layout harder to navigate.
- Build one unified interface-agnostic acceptance harness.
  Rejected because CLI and MCP still differ materially in transport, result shape, and failure signaling.

### 7. Keep MCP schemas aligned with service/CLI result models, but do not expand the MCP tool surface

Decision:
Limit MCP work in this change to stronger acceptance coverage and any schema/result adjustments required by shared output and policy enforcement. Do not add new MCP tools such as CLI-only `list`/`show` analogs unless the requirements explicitly demand them later.

Rationale:
Feature 0007 is mostly about polish and acceptance, not broadening the interface contract again. The current MCP surface already covers the required nine tools, so the main task is to keep it consistent with shared services and verify it thoroughly.

Alternatives considered:
- Add MCP tools mirroring every new CLI command.
  Rejected because the feature brief does not require it and it would expand scope unnecessarily.
- Ignore MCP while polishing the CLI.
  Rejected because the acceptance criteria explicitly require MCP parity verification.

## Risks / Trade-offs

- [A shared presentation layer can add indirection to a currently simple CLI] -> Keep it narrow and result-focused, with commands still owning argument parsing and service invocation.
- [Path normalization rules may break tests or workflows that previously relied on permissive temp paths] -> Add explicit allowed-root test coverage and keep fixture/config setup clear in acceptance tests.
- [Introducing more exception classes can complicate service error handling] -> Use a small, intentional hierarchy tied directly to the documented exit-code matrix.
- [Checked-in binary fixtures can be harder to update than generated test files] -> Keep the corpus minimal, deterministic, and focused on acceptance coverage rather than every edge case.
- [Reorganizing the test layout can create churn in existing imports and helpers] -> Move acceptance coverage incrementally and preserve shared helper functions where practical.

## Migration Plan

1. Extend configuration and shared path-validation helpers with allowed-root and output-root policy support.
2. Introduce structured summary models plus any service methods needed for `list` and `show`.
3. Add a CLI presentation layer and update commands to support `--json`, `--quiet`, and the final exit-code mapping.
4. Add the missing `list` and `show` commands and update interface-specific docs/tests around output behavior.
5. Introduce deterministic fixture files under `tests/fixtures/` and migrate acceptance-oriented CLI and MCP tests to use them.
6. Expand CLI and MCP acceptance suites to cover the final workflow, schema, and policy-refusal expectations.

Rollback:
Revert the new CLI presentation helpers, config fields, path-policy enforcement, fixture-corpus changes, and acceptance-suite additions. Existing core indexing, read, write, and MCP workflows remain intact because this change layers polish and contract enforcement on top of the current architecture.

## Open Questions

- Should `allowed_roots` govern indexing directories as well as direct read/write targets, or should indexing have a distinct policy field?
- Should `--quiet` suppress successful structured output entirely for commands like `search`, `list`, and `show`, or should it only suppress non-essential informational lines around otherwise requested results?
- Should the acceptance refactor preserve the current flat `tests/test_*.py` files for backward continuity while adding `tests/cli/` and `tests/mcp/`, or should interface-level tests move completely to the new directory structure in one pass?
