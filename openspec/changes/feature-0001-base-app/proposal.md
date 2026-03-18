## Why

The project needs a concrete application foundation before any format-specific extraction or patching work can be implemented safely. Establishing the package structure, configuration model, index store, file discovery, and diagnostics now creates a stable base for later DOCX, PPTX, XLSX, and MCP features.

## What Changes

- Create the initial `offagent` package layout and CLI entrypoint for the shared application core.
- Add configuration loading with file-backed defaults and environment-variable overrides.
- Add the foundational domain models and locator parsing stubs used by indexing, search, and patch flows.
- Create the SQLite metadata and FTS5 schema plus connection management for the local structural index.
- Add file discovery for Office documents under configured roots.
- Add a `doctor` command to validate runtime prerequisites, storage setup, and document root access.

## Capabilities

### New Capabilities
- `app-foundation`: Project skeleton, shared domain models, service stubs, and CLI wiring for the local-first Office agent.
- `local-index-store`: SQLite schema creation and storage access for documents, items, and FTS-backed search data.
- `config-and-diagnostics`: Configuration loading, Office file discovery, and environment checks exposed through `office-agent doctor`.

### Modified Capabilities
None.

## Impact

This change affects the Python package layout under `src/offagent/`, CLI packaging in `pyproject.toml`, local SQLite usage, configuration handling, and the initial test suite for config loading, schema creation, file discovery, and locator parsing.
