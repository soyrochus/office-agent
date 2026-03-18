# Office-Agent
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Server-orange.svg)](https://gofastmcp.com/getting-started/welcome)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![FOSS Pluralism](https://img.shields.io/badge/FOSS-Pluralism-purple.svg)](FOSS_PLURALISM_MANIFESTO.md)
[![OpenSpec](https://img.shields.io/badge/OpenSpec-Used-black.svg)](https://openspec.dev/)

Office-Agent (`offagent`) is a local-first Office document tool with a shared application core and a CLI entrypoint, `office-agent`.

The project is being built incrementally. The current implementation includes:

- project configuration and environment diagnostics
- a local SQLite + FTS5 index
- DOCX paragraph extraction and indexing
- DOCX search, locate, read, replace, and append operations
- PPTX text-shape extraction and indexing
- PPTX search, locate, read, replace, and append operations

Current scope is intentionally narrow. DOCX and PPTX are the currently implemented document formats. XLSX, MCP integration, and versioned write outputs are not implemented yet.

## Current Features

### Base App

- `office-agent doctor` checks required imports, SQLite availability, FTS5 support, index path writability, and configured document roots
- configuration loads from a TOML file with environment variable overrides
- Office file discovery supports `.docx`, `.pptx`, and `.xlsx` roots at the base layer

### DOCX Workflow

- index a `.docx` file or a directory of `.docx` files
- reindex a changed `.docx` file
- search indexed DOCX paragraph content through SQLite FTS5
- locate a paragraph directly by paragraph number
- read the current paragraph text from the source document
- replace a paragraph while preserving the first run's character formatting
- append text to the last run of a paragraph, or create a run for an empty paragraph

DOCX indexing uses paragraph-level item ids in the form `para:<n>`. Empty paragraphs are included so paragraph numbering stays stable.

### PPTX Workflow

- index a `.pptx` file or a directory of supported Office files
- search indexed PowerPoint text-frame content through SQLite FTS5
- locate editable text-bearing shapes by slide number, with optional shape id narrowing
- read the current text-frame content from the source presentation
- replace the full text-frame content of one shape
- append text to an existing editable text frame

PPTX indexing uses shape-level item ids in the form `slide:<n>:shape:<id>`. Only shapes with text frames are indexed. Tables, charts, images, SmartArt, and other non-text shapes are excluded, and PPTX write attempts to those targets fail with `target not editable`.

## Installation

The project uses `uv` in development.

```bash
uv sync
```

Run the CLI with:

```bash
uv run office-agent --help
```

## Configuration

The CLI accepts an optional config file via `--config <path>`.

Example `office-agent.toml`:

```toml
[offagent]
index_path = ".offagent/index.sqlite3"
document_roots = ["./docs"]
```

Environment variables override file settings:

- `OFFAGENT_CONFIG`
- `OFFAGENT_INDEX_PATH`
- `OFFAGENT_DOCUMENT_ROOTS`

`OFFAGENT_DOCUMENT_ROOTS` uses the platform path separator, for example `:` on macOS/Linux.

## CLI

### Doctor

```bash
uv run office-agent doctor
uv run office-agent doctor --config office-agent.toml
```

### Index And Reindex

```bash
uv run office-agent index ./docs
uv run office-agent index ./docs/sample.docx
uv run office-agent index ./docs/sample.pptx
uv run office-agent reindex ./docs/sample.docx
uv run office-agent reindex ./docs/sample.pptx
```

### Search

```bash
uv run office-agent search "supplier shall"
uv run office-agent search "supplier shall" --type docx
uv run office-agent search "supplier shall" --type pptx
uv run office-agent search "supplier shall" --type docx --doc ./docs/sample.docx
uv run office-agent search "supplier shall" --type pptx --doc ./docs/sample.pptx
```

The current implementation returns item hits with item id, score, and preview text.

### Locate

```bash
uv run office-agent locate --doc ./docs/sample.docx --paragraph 3
uv run office-agent locate --doc ./docs/sample.pptx --slide 1
uv run office-agent locate --doc ./docs/sample.pptx --slide 1 --shape 7
```

### Read

```bash
uv run office-agent read --doc ./docs/sample.docx --item para:3
uv run office-agent read --doc ./docs/sample.pptx --item slide:1:shape:7
```

### Replace

```bash
uv run office-agent replace --doc ./docs/sample.docx --item para:3 --text "Updated paragraph text."
uv run office-agent replace --doc ./docs/sample.pptx --item slide:1:shape:7 --text "Updated slide text."
```

### Append

```bash
uv run office-agent append --doc ./docs/sample.docx --item para:3 --text " Additional text."
uv run office-agent append --doc ./docs/sample.pptx --item slide:1:shape:7 --text "\nAdditional slide text."
```

At the moment, DOCX and PPTX `replace` and `append` write in place and then reindex the updated file.

## Development

Run the test suite with:

```bash
uv run pytest
```

The test suite is written in `pytest` and includes:

- configuration and diagnostics coverage
- SQLite store coverage
- DOCX adapter tests
- DOCX service workflow tests
- PPTX adapter tests
- PPTX service workflow tests
- CLI round-trip tests for DOCX and PPTX

## Project Status

Implemented:

- shared CLI/application-core structure
- configuration and doctor checks
- SQLite index bootstrap and FTS5-backed search
- DOCX paragraph extraction and editing workflow
- PPTX text-shape extraction and editing workflow

Not implemented yet:

- XLSX support
- MCP interface
- versioned output paths for write operations
- richer locator resolution beyond the current DOCX and PPTX flows


## Principles of Participation

Everyone is invited and welcome to contribute: open issues, propose pull requests, share ideas, or help improve documentation. Participation is open to all, regardless of background or viewpoint.  

This project follows the [FOSS Pluralism Manifesto](./FOSS_PLURALISM_MANIFESTO.md),  
which affirms respect for people, freedom to critique ideas, and space for diverse perspectives.  

## License and Copyright

Copyright (c) 2026, Iwan van der Kleijn

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
