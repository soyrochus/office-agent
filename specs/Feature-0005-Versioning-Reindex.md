# Feature 0005 — Versioning & Reindex

## Goal

Make all write operations safe by default: every write produces a versioned output file, and the index is automatically updated to reflect the new version.

## Scope

### Included

* `storage/versioning.py`:
  * versioned output path generator: `<name>.edited.<timestamp>.<ext>`
  * timestamp format: `YYYYMMDD-HHMMSSffffff` (UTC, sortable)
  * configurable output directory (defaults to same directory as source)
* `output_mode` parameter on all write service methods:
  * `"versioned"` (default) — write to versioned sibling path
  * `"inplace"` — overwrite source; only permitted if config explicitly allows it
* Automatic reindex of the output file after every successful write
* Stale locator detection:
  * before applying a patch, reload source file
  * verify `content_hash` matches what was indexed
  * if mismatch, attempt to re-resolve target item id in updated content
  * if target no longer exists, fail with "stale locator" error (exit code 3)
* Config additions:
  * `output_directory` — where versioned files are written
  * `allow_inplace_overwrite` — boolean, default false

### Excluded

* Diff or rollback between versions (optional later per spec §8.2)
* Batch operations
* MCP interface (F6)

## Write Flow (updated)

1. Resolve `ItemRef` from locator or item id
2. Load source file; verify content hash
3. Apply patch to in-memory document object
4. Determine output path via versioning policy
5. Save to output path
6. Reindex output file (update `documents` + `items` + `items_fts`)
7. Return output path, change summary, new document id/version

## Acceptance Criteria

* Every `replace`, `append`, and `write-cell` call produces a file named `<name>.edited.<timestamp>.<ext>` in the configured output directory
* Source file is not modified unless `allow_inplace_overwrite = true` in config
* Reindex runs automatically; `office-agent search` returns results from the new version
* Modifying the source file externally between index and write triggers "stale locator" failure
* Unit tests cover: version path generation, content hash comparison, stale locator detection, reindex-after-write
