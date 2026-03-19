## Why

The current write workflows update source files in place, which makes edits harder to audit, easier to lose, and unsafe when indexed content has drifted from the file on disk. Adding versioned outputs and stale-locator checks now is necessary before the product grows further, because every editing flow depends on predictable write safety and reliable reindex behavior.

## What Changes

- Add a versioned output policy for all write operations so `replace`, `append`, and `write-cell` save to `<name>.edited.<timestamp>.<ext>` by default instead of overwriting the source file.
- Add configuration for versioned output location plus an explicit `allow_inplace_overwrite` escape hatch for workflows that intentionally need in-place writes.
- Extend write services to reindex the newly written output file automatically after every successful patch.
- Add stale-locator detection before writes by validating the indexed content hash against the current source file and failing safely when the target can no longer be resolved.
- Add tests covering version path generation, overwrite policy enforcement, stale-locator failures, and reindex-after-write behavior across the supported document formats.

## Capabilities

### New Capabilities
- `versioned-write-outputs`: Generate versioned output paths for all write operations, support configurable output directories, and gate in-place overwrite behind explicit configuration.
- `write-reindex-synchronization`: Reindex each successfully written output file automatically so search and subsequent locate/read flows reflect the new version.
- `stale-locator-detection`: Validate indexed content hashes before writes, attempt safe target re-resolution when content has changed, and fail with a stale-locator error when the original target is no longer valid.

### Modified Capabilities
None.

## Impact

This change affects application service write workflows, configuration loading and validation, document adapter save-path handling, output file naming behavior, index refresh paths after writes, and the CLI-visible write semantics for DOCX, PPTX, and XLSX operations. It also adds cross-format test coverage for safe versioned output and stale-locator handling.
