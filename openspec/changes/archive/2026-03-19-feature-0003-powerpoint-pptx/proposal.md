## Why

The project needs a PowerPoint workflow that matches the same index-first, deterministic editing model already established for DOCX so presentation content can be searched and updated without treating slides as opaque files. Implementing PPTX next validates that the shared application core can support a second Office format with different structural rules while preserving one consistent service and CLI architecture.

## What Changes

- Add a PPTX adapter based on `python-pptx` that traverses slides and extracts only text-bearing shapes with stable `slide:{slide_number}:shape:{shape_id}` item identifiers.
- Extend indexing and application services to persist PPTX text-shape items, search them through the local store, resolve slide and shape locators, and read current text frame content from source files.
- Add PPTX replace and append operations for editable text-frame shapes with explicit rejection of non-text targets.
- Extend the CLI so indexing, reindexing, search, locate, read, replace, and append workflows support `.pptx` documents.
- Add adapter and service tests covering text-shape extraction, search and locate flows, editable-shape patching, and reopen verification.

## Capabilities

### New Capabilities
- `pptx-text-shape-extraction`: Extract editable PPTX text-bearing shapes with slide metadata, shape metadata, and stable item ids for indexing.
- `pptx-search-and-read`: Index PPTX text-shape items and expose search, locate, and read workflows through the shared service layer and CLI.
- `pptx-text-shape-editing`: Replace and append text for PPTX text-frame shapes while rejecting non-editable shape targets.

### Modified Capabilities
None.

## Impact

This change affects `python-pptx` integration, document adapters, index population paths, service-layer document handling, CLI command behavior for multi-format indexing and lookup, and the test fixtures needed to verify PowerPoint extraction and text-frame edits. It also expands the product from one implemented Office format to a second with shape-based rather than paragraph-based document structure.
