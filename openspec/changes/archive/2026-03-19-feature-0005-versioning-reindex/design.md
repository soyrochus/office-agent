## Context

The current implementation now supports DOCX, PPTX, and XLSX indexing plus direct write operations, but every write path still saves in place and reindexes the same source file immediately afterward. `src/offagent/app/services.py` already computes and stores a `content_hash` during indexing, and all adapters already accept an optional `output_path`, but that information is not yet used to enforce write safety or generate versioned outputs. This change needs to tighten every write workflow across formats without breaking the existing separation between adapters, service orchestration, configuration loading, and the SQLite-backed index.

Constraints:
- Business logic remains in the application service layer; adapters continue to own format-specific read and write mechanics.
- Versioning behavior must apply consistently to DOCX, PPTX, and XLSX write operations.
- The source file should remain unchanged by default; in-place overwrite must require explicit configuration.
- Stale-locator detection must compare the current source file against the indexed version before patching.
- Automatic reindexing must target the newly written versioned file so search and future reads resolve against the updated artifact.

## Goals / Non-Goals

**Goals:**
- Add a versioned output path policy that all write flows can use consistently across supported document formats.
- Extend configuration so users can choose an output directory and explicitly opt into in-place overwrite when needed.
- Add stale-locator protection by validating indexed content hashes before writes and failing safely when a target can no longer be trusted.
- Reindex every successful write output automatically so the local store reflects the new version immediately.
- Add focused tests for version path generation, overwrite policy enforcement, stale-locator detection, and reindex-after-write behavior.

**Non-Goals:**
- Full document version history, rollback, or diff views between saved versions.
- Batch edits or multi-item write transactions.
- Rich conflict resolution that attempts semantic relocation beyond deterministic item-id re-resolution.
- MCP-specific write safety behavior.
- Refactoring the whole indexing model beyond what is necessary to add safe versioning and stale-locator checks.

## Decisions

### 1. Add a shared versioning module rather than duplicating naming logic in adapters

Decision:
Create a dedicated module such as `src/offagent/storage/versioning.py` to generate output paths of the form `<name>.edited.<timestamp>.<ext>` using UTC timestamps and optional configured output directories.

Rationale:
Every adapter already accepts an `output_path`, so the service layer only needs one authoritative path-generation utility. Centralizing path logic avoids duplicated naming behavior and keeps adapters format-focused.

Alternatives considered:
- Generate versioned names separately inside each adapter.
  Rejected because it would repeat the same policy three times and make config-driven path behavior harder to keep consistent.
- Generate output paths inline inside each service write method.
  Rejected because the policy is cross-cutting and deserves one reusable implementation.

### 2. Keep adapters responsible for writing to a provided target path

Decision:
Leave DOCX, PPTX, and XLSX adapters responsible for mutating in-memory documents and saving them to the `output_path` chosen by the service layer.

Rationale:
The existing adapter boundary is already correct: services orchestrate workflow and persistence, while adapters know how to save a given document format. Versioning changes where the file is written, not how each file format is patched.

Alternatives considered:
- Move all save-path logic into adapters along with overwrite policy decisions.
  Rejected because overwrite policy is application behavior, not format behavior.
- Have services manipulate raw document libraries directly to control save semantics.
  Rejected because it would violate the format adapter boundary.

### 3. Extend configuration with explicit write policy controls

Decision:
Add `output_directory` and `allow_inplace_overwrite` to `AppConfig`, support them in file and environment loading, and treat versioned output as the default write mode when no explicit override is requested.

Rationale:
Write safety should be a configuration-backed application policy rather than an ad hoc CLI convention. Putting the policy in config makes behavior predictable across tests, local usage, and future interface layers.

Alternatives considered:
- Always write versioned files with no configuration.
  Rejected because some workflows may still need controlled in-place overwrite.
- Add CLI flags only and skip config support.
  Rejected because the policy is cross-interface and should not depend on one frontend.

### 4. Validate the indexed content hash before every write

Decision:
Before patching, load the indexed document row, compare its stored `content_hash` to the current source file hash, and treat a mismatch as a stale-target workflow that must be resolved before writing.

Rationale:
`content_hash` is already available in the document metadata. Using it closes the gap between indexing time and write time and prevents applying edits against files that have changed outside the tool.

Alternatives considered:
- Ignore source drift and always patch the current file.
  Rejected because it can silently apply edits to the wrong content after external changes.
- Compare only modified time.
  Rejected because timestamps are weaker and less deterministic than a content hash.

### 5. Re-resolve by deterministic item id only, then fail with a stale-locator error

Decision:
When the content hash has changed, re-extract or reindex the current source file and attempt to resolve the same item id in the updated content. If the item id no longer exists, fail with a dedicated stale-locator error and CLI exit code 3.

Rationale:
The current item models already rely on deterministic ids such as `para:{n}`, `slide:{slide}:shape:{id}`, and `sheet:{name}!{cell}`. Reusing the same item id is the narrowest safe recovery path and avoids inventing fuzzy conflict resolution in this change.

Alternatives considered:
- Automatically patch the closest textual match.
  Rejected because heuristic relocation is risky and not justified for the current product scope.
- Always fail on any content-hash mismatch with no re-resolution attempt.
  Rejected because deterministic ids can still remain valid after unrelated external changes.

### 6. Introduce explicit output modes in service-layer write methods

Decision:
Extend `replace_item_text`, `append_item_text`, and `write_cell_value` with an `output_mode` concept, where `"versioned"` is the default and `"inplace"` is allowed only when configuration explicitly permits it.

Rationale:
This makes write policy visible at the workflow boundary without leaking versioning concerns into CLI formatting or adapter internals. It also matches the feature brief’s requirement that services support both safe defaults and explicit overwrite control.

Alternatives considered:
- Remove in-place writing entirely.
  Rejected because the feature brief explicitly keeps it as a gated option.
- Keep implicit defaults only and omit an output-mode parameter from services.
  Rejected because tests and future callers benefit from an explicit policy input.

### 7. Reindex the written output as the new authoritative document for subsequent queries

Decision:
After a successful patch, index the newly written output file and return its path in `PatchResult`, while leaving the original indexed source record untouched unless the write mode was truly in-place.

Rationale:
Search, locate, and read should reflect the new version immediately, and the service layer already has the index/update pipeline needed to do that. Treating versioned outputs as new indexed documents also preserves the original source artifact for comparison and audit.

Alternatives considered:
- Replace the original indexed record even for versioned outputs.
  Rejected because it would obscure the distinction between the source file and its derived edited version.
- Delay reindexing until a later manual refresh.
  Rejected because automatic synchronization is one of the core goals of the change.

## Risks / Trade-offs

- [Versioned outputs can increase file clutter in source directories] -> Support a configurable output directory and keep the naming scheme sortable and predictable.
- [Paragraph-based DOCX ids may become invalid after external edits] -> Re-resolve by deterministic item id only and fail clearly with a stale-locator error when the target disappears.
- [Reindexing each new version can accumulate many indexed document rows] -> Accept additive indexing for now and defer lifecycle cleanup policies to a later change.
- [In-place overwrite remains a footgun if exposed too broadly] -> Gate it behind explicit configuration and keep the default write mode versioned.
- [Cross-format write policy changes can cause regressions in existing workflows] -> Cover all three formats with shared service and CLI tests for both versioned output and stale-target handling.

## Migration Plan

1. Add shared versioning utilities and extend configuration with output-directory and overwrite-policy fields.
2. Introduce stale-locator validation helpers in the service layer using stored `content_hash` values.
3. Extend DOCX, PPTX, and XLSX write workflows to choose an output path by policy, patch through adapters, and reindex the written file.
4. Update CLI write commands to surface stale-locator failures and any new output-mode behavior.
5. Add cross-format tests for version path generation, versioned write outputs, stale-locator errors, and reindex-after-write synchronization.

Rollback:
Revert the versioning module, configuration additions, and write-flow changes so adapters and services return to in-place write behavior. Existing indexing and read workflows remain intact because this change layers on top of the current architecture.

## Open Questions

- Should versioned output naming preserve the original extension case exactly, or normalize it while generating edited filenames?
- Should automatic re-resolution on content-hash mismatch update the stored source record before the write, or only use the fresh extraction transiently for validation?
- Should CLI users be able to request `--output-mode inplace` per command immediately, or should the initial implementation rely only on configuration defaults and policy checks?
