# Feature 0001 — Base App

## Goal

Establish the project skeleton, configuration system, storage schema, file discovery, and environment diagnostics. Every subsequent feature builds on this foundation.

## Scope

### Included

* `pyproject.toml` with package name `offagent`, console script `office-agent`, and core dependencies (`typer`, `sqlite3` stdlib, `pydantic`, `python-dotenv`)
* Module structure under `src/offagent/`:
  * `config.py` — config loader (file + env var overrides)
  * `domain/models.py` — `DocumentRef`, `ItemRef`, `SearchHit`, `PatchOperation`
  * `domain/locators.py` — locator parsing stubs
  * `indexing/store.py` — SQLite schema creation and connection management
  * `interfaces/cli.py` — Typer app entrypoint with subcommand groups
  * `app/services.py` — service layer stubs
* SQLite schema: `documents`, `items`, `items_fts` (FTS5)
* File discovery: walk a root path, filter by `.docx`, `.pptx`, `.xlsx`, collect path + modified time
* `doctor` CLI command: validate required libraries import, SQLite availability, index path writable, configured document roots readable

### Excluded

* Any format-specific extraction (F2–F4)
* Write operations
* MCP interface

## CLI Commands

```
office-agent doctor
```

## Acceptance Criteria

* `office-agent doctor` runs and reports pass/fail for each check
* SQLite schema is created on first run if absent
* Config loads from file with env var override working
* File discovery returns correct file list for a directory containing mixed Office files
* Unit tests cover: config loading, schema creation, file discovery, locator stub parsing
