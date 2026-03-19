## Why

The core DOCX, PPTX, XLSX, and MCP workflows now exist, but the product still lacks the final polish required for predictable user-facing behavior and full acceptance coverage. This change is needed now to close the remaining gaps in CLI completeness, exit-code correctness, path safety, fixture stability, and end-to-end verification before the tool can be treated as a complete local-first Office workflow.

## What Changes

- Complete the CLI surface with `list` and `show` commands plus consistent human-readable output behavior across commands.
- Add `--json` and `--quiet` output modes to the CLI so structured automation and low-noise scripting use the same command surface as interactive users.
- Enforce the defined exit-code contract across all commands, separating invalid arguments, not-found conditions, not-editable targets, and policy-refused writes.
- Add configurable security path guards so reads and writes are normalized against allowed roots and unsafe paths are rejected before document operations run.
- Establish deterministic, version-controlled golden fixtures under `tests/fixtures/` for DOCX, PPTX, and XLSX workflows.
- Expand CLI and MCP test coverage to exercise the full command and tool surface, including acceptance-path assertions for output formatting, exit codes, policy guards, and versioned writes.

## Capabilities

### New Capabilities
- `cli-output-modes`: Add `--json` and `--quiet` output handling across structured CLI commands with consistent human-readable formatting in the default mode.
- `document-summary-commands`: Add `office-agent list` and `office-agent show` so users can inspect indexed documents and item-level details directly from the CLI.
- `security-path-guards`: Enforce normalized allowed-root and output-root policy checks for document reads and writes before file operations execute.
- `golden-fixture-corpus`: Add deterministic DOCX, PPTX, and XLSX fixture files under version control for acceptance-style CLI and MCP test coverage.
- `acceptance-test-coverage`: Add CLI and MCP integration coverage for the full supported workflow surface, including exit-code, schema, and policy-refusal assertions.

### Modified Capabilities
- `config-and-diagnostics`: Extend configuration requirements to support `allowed_roots` and any output-root policy fields needed by the new path guards.
- `app-foundation`: Tighten the CLI-facing command contract to enforce the final exit-code matrix and consistent output behavior across existing workflows.
- `mcp-service-tools`: Extend acceptance coverage expectations so the MCP tool surface is verified against the final fixture corpus and schema contract.
- `mcp-error-mapping`: Refine failure expectations so MCP error behavior stays aligned with the final service and policy checks introduced by this change.

## Impact

This change affects CLI command registration and output formatting, configuration loading and validation, service-layer path-guard enforcement, the on-disk fixture corpus, and the automated CLI and MCP test layout. It also modifies user-visible exit-code semantics and expands the final acceptance boundary for both human and programmatic interfaces.
