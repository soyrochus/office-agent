## 1. Configuration And Path Guard Foundation

- [x] 1.1 Extend the configuration model and loader with `allowed_roots` and any output-root policy fields needed for guarded reads and writes
- [x] 1.2 Add normalized shared path-validation helpers that resolve symlinks and traversal before indexing, read, or write workflows execute
- [x] 1.3 Introduce explicit policy-refused and argument/error classes that can support the final CLI exit-code matrix
- [x] 1.4 Add focused tests for configuration precedence and path-guard validation behavior

## 2. Service Summary Models And Read Paths

- [x] 2.1 Add structured service-layer document summary and item detail results needed by `list` and `show`
- [x] 2.2 Implement shared service methods for listing indexed documents with item counts and showing one document or one indexed item
- [x] 2.3 Ensure read-oriented service flows enforce allowed-root policy consistently for direct document access and indexed lookups

## 3. CLI Surface, Output Modes, And Exit Codes

- [x] 3.1 Add a CLI presentation layer that can render shared results in default human-readable, JSON, and quiet modes
- [x] 3.2 Add shared `--json` and `--quiet` options to structured CLI commands and update existing commands to use the new formatter
- [x] 3.3 Implement `office-agent list` and `office-agent show` on top of the shared service summary methods
- [x] 3.4 Update CLI error handling so invalid arguments, not-found targets, not-editable targets, and policy-refused operations map to exit codes `2`, `3`, `4`, and `5`

## 4. Fixture Corpus And Test Layout

- [x] 4.1 Add deterministic DOCX, PPTX, and XLSX golden fixtures under `tests/fixtures/` that satisfy the acceptance coverage requirements
- [x] 4.2 Refactor shared test helpers so CLI and MCP acceptance tests can use the checked-in fixture corpus without regenerating binary files during normal runs
- [x] 4.3 Preserve or adapt the targeted generated fixtures in unit/service tests only where they still add value beyond the golden corpus

## 5. Acceptance Coverage And Verification

- [x] 5.1 Expand CLI acceptance coverage for `index`, `reindex`, `search`, `locate`, `read`, `replace`, `append`, `write-cell`, `list`, `show`, and `doctor`
- [x] 5.2 Add CLI acceptance assertions for JSON output, quiet mode, and the full documented exit-code matrix
- [x] 5.3 Expand MCP integration coverage to validate tool schemas, result structures, and policy-refusal/error behavior against the golden fixture corpus
- [x] 5.4 Verify cross-interface parity for the documented index → search → locate → read → replace cycle and versioned-write behavior
- [x] 5.5 Run the relevant test suite and confirm the final polish-and-acceptance criteria end to end
