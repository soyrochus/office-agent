## 1. DOCX Foundation

- [x] 1.1 Add the `python-docx` dependency and create the `src/offagent/adapters/` package with a DOCX adapter module
- [x] 1.2 Define or extend shared domain structures needed for DOCX paragraph items, locators, and patch payloads
- [x] 1.3 Add focused DOCX test fixtures that cover normal paragraphs, empty paragraphs, headings, and patchable content

## 2. DOCX Adapter

- [x] 2.1 Implement DOCX paragraph extraction in `adapters/docx_adapter.py` with stable `para:{n}` item ids and paragraph metadata
- [x] 2.2 Ensure extraction includes empty paragraphs and excludes table cell content
- [x] 2.3 Implement paragraph read helpers for resolved DOCX items
- [x] 2.4 Implement paragraph replace behavior that preserves the first run's character formatting
- [x] 2.5 Implement paragraph append behavior that appends to the last run or creates a run for empty paragraphs

## 3. Index And Search Integration

- [x] 3.1 Extend `indexing/store.py` with document upsert and document-scoped item replacement operations for DOCX indexing
- [x] 3.2 Extend `indexing/store.py` with FTS-backed DOCX paragraph search queries returning document and item metadata
- [x] 3.3 Add service-layer indexing and reindexing flows for individual DOCX files and directories
- [x] 3.4 Add service-layer search, locate, and read flows that normalize DOCX results to `ItemRef` and `SearchHit`

## 4. Editing Workflows

- [x] 4.1 Add service-layer replace and append workflows that resolve a DOCX paragraph item before patching
- [x] 4.2 Ensure edit workflows reopen or otherwise verify the updated DOCX content after patching
- [x] 4.3 Define the temporary-path or in-place write behavior for this feature and apply it consistently in services and adapter calls

## 5. CLI Surface

- [x] 5.1 Add `office-agent index <path>` and `office-agent reindex <path>` commands for DOCX indexing flows
- [x] 5.2 Add `office-agent search <query> [--type docx] [--doc <file>]` and `office-agent locate --doc <file> --paragraph <n>` commands
- [x] 5.3 Add `office-agent read --doc <file> --item <item-id>` command for DOCX paragraphs
- [x] 5.4 Add `office-agent replace --doc <file> --item <item-id> --text "<text>"` and `office-agent append --doc <file> --item <item-id> --text "<text>"` commands

## 6. Testing And Verification

- [x] 6.1 Add pytest coverage for DOCX extraction, including empty paragraphs, style metadata, heading flags, and table exclusion
- [x] 6.2 Add pytest coverage for DOCX indexing, search, locate, and read workflows
- [x] 6.3 Add pytest coverage for DOCX replace and append patch operations, including reopen verification
- [x] 6.4 Run the DOCX-focused pytest suite and verify the CLI commands satisfy the acceptance criteria with sample documents
