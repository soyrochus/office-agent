Feature Sequence
F1 — Base App
Project skeleton, pyproject.toml, config loader, SQLite schema (documents, items, items_fts), file discovery, doctor CLI command, logging infrastructure.

Done when: office-agent doctor runs and reports environment health.

F2 — Word (DOCX)
DOCX extraction (paragraphs, style, heading flag), index/reindex, CLI index, search, locate, read, replace, append for paragraphs only.

Done when: full read/write round-trip on a .docx fixture works from CLI.

F3 — PowerPoint (PPTX)
PPTX extraction (text-bearing shapes only), extend index, CLI locate by slide/shape, replace/append for text frames. Reject non-text shapes explicitly.

Done when: same round-trip on a .pptx fixture.

F4 — Excel (XLSX)
XLSX cell extraction (non-empty values + formulas as text), extend index, CLI locate by sheet/cell, write-cell. Append-to-cell guarded by string-compatible check.

Done when: same round-trip on a .xlsx fixture.

F5 — Versioning & Reindex
Versioned output (<name>.edited.<timestamp>.<ext>), automatic reindex after write, overwrite policy config, stale-locator conflict detection.

Done when: every write produces a versioned file and the index reflects the new version.

F6 — MCP Interface
Thin MCP server over existing services (stdio transport), all required tool schemas (index_documents, search_documents, locate_item, read_item, replace_text, append_text, write_cell, list_documents, refresh_document).

Done when: MCP tools pass schema validation and match CLI behavior for all three formats.

F7 — Polish & Acceptance
Golden fixture corpus, CLI tests, MCP integration tests, list/show commands, --json/--quiet output modes, exit codes, security path guards.

Done when: all acceptance criteria in §19 pass.

