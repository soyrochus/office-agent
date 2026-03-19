## Why

The project needs a complete Word document path from extraction through editing so the shared application core can prove it supports real Office workflows, not just environment setup. Implementing the DOCX path now validates the index-first architecture on a single format before expanding to PowerPoint, Excel, or MCP.

## What Changes

- Add a DOCX adapter based on `python-docx` that extracts paragraphs in document order, including empty paragraphs, with stable `para:{n}` item identifiers.
- Extend indexing and application services to ingest DOCX paragraph items, search them through the local store, resolve paragraph locators, and read current paragraph text from source files.
- Add paragraph-level write operations for DOCX replace and append behavior using deterministic item ids.
- Add CLI commands for indexing, reindexing, search, locate, read, replace, and append on DOCX content.
- Add adapter and service tests covering extraction, query flows, and paragraph patch verification.

## Capabilities

### New Capabilities
- `docx-paragraph-extraction`: Extract DOCX paragraphs with stable item ids, style metadata, and heading flags for indexing.
- `docx-search-and-read`: Index DOCX paragraph items and expose search, locate, and read workflows through the service layer and CLI.
- `docx-paragraph-editing`: Replace and append DOCX paragraph text while preserving the supported formatting behavior for paragraph edits.

### Modified Capabilities
None.

## Impact

This change affects `python-docx` integration, document adapters, index population paths, application services, CLI command surface, and the test fixtures needed to verify DOCX extraction and paragraph edits. It also expands the base app from diagnostics-only behavior into the first end-to-end document workflow.
