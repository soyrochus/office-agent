## Why

The project already supports end-to-end DOCX and PPTX workflows, but Excel files are still limited to discovery only despite being part of the intended Office surface from the start. Adding XLSX support now completes the planned third core document path and validates that the shared index-first architecture can handle workbook and cell-based content, not just paragraphs and slide shapes.

## What Changes

- Add an XLSX adapter based on `openpyxl` that traverses worksheets and extracts non-empty cells with stable `sheet:{sheet_name}!{coordinate}` item identifiers.
- Extend indexing and application services to persist XLSX cell items, search them through the local store, resolve sheet and cell locators, and read current cell values from source files.
- Add XLSX write operations for direct cell updates plus guarded append behavior for string-compatible cells, with explicit rejection for unsupported numeric or formula append cases.
- Extend the CLI so indexing, reindexing, search, locate, read, write-cell, and append workflows support `.xlsx` documents.
- Add adapter and service tests covering cell extraction, search and locate flows, write-cell persistence, and append guard behavior.

## Capabilities

### New Capabilities
- `xlsx-cell-extraction`: Extract non-empty XLSX cells across worksheets with sheet metadata, cell metadata, formula text, and stable item ids for indexing.
- `xlsx-search-and-read`: Index XLSX cell items and expose search, locate, and read workflows through the shared service layer and CLI.
- `xlsx-cell-editing`: Update XLSX cell values and allow append only for string-compatible cells while rejecting unsupported append targets.

### Modified Capabilities
None.

## Impact

This change affects `openpyxl` dependency management, document adapters, index population paths, shared application services, CLI command handling for multi-format document workflows, and the fixtures and tests needed to verify Excel extraction and cell edits. It also completes the initial Office-format trilogy by extending the product from DOCX and PPTX into workbook-oriented XLSX handling.
