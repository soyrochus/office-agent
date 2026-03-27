# Feature 0007 — Polish & Acceptance

## Goal

Complete the CLI surface, harden output formatting and exit codes, enforce security path guards, establish the golden fixture corpus, and achieve full test coverage across CLI and MCP.

## Scope

### Included

#### CLI completeness

* `office-agent list` — list all indexed documents (id, path, type, modified time, item count)
* `office-agent show --doc <file>` — show document summary and item count
* `office-agent show --doc <file> --item <item-id>` — show item details
* `--json` output mode on all commands that return structured data
* `--quiet` output mode on all commands (suppress informational output, errors only)
* Consistent output formatting across all commands in default human-readable mode

#### Exit codes (enforced across all commands)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Operational failure (IO error, parse error, unexpected exception) |
| 2 | Invalid arguments |
| 3 | Target not found |
| 4 | Target not editable |
| 5 | Patch refused by policy |

#### Security path guards

* Configurable `allowed_roots` list in config
* All file paths normalised (resolve symlinks, `..` traversal) before any operation
* Writes rejected if output path falls outside configured output roots
* Reads rejected if document path falls outside configured allowed roots
* No file deletion in any code path
* No macro execution, no embedded-object processing, no external link dereferencing

#### Golden fixture corpus (`tests/fixtures/`)

* `sample.docx` — at least 10 paragraphs including headings and body text, no tables
* `sample.pptx` — at least 3 slides with title, subtitle, and text-box shapes; at least one non-text shape present
* `sample.xlsx` — at least 2 sheets with text cells, numeric cells, and one formula cell

Fixtures must be deterministic and version-controlled. Do not regenerate them between test runs.

#### CLI test suite (`tests/cli/`)

Full command coverage against fixture corpus:
* `index`, `reindex`
* `search` (plain, `--type`, `--doc`)
* `locate` (DOCX paragraph, PPTX slide/shape, XLSX sheet/cell)
* `read`
* `replace`, `append`, `write-cell`
* `list`, `show`
* `doctor`
* Exit code assertions for not-found, not-editable, and policy-refused scenarios

#### MCP integration test suite (`tests/mcp/`)

* Start MCP server as subprocess
* Invoke each tool via the MCP test client
* Validate tool input schemas match defined Pydantic models
* Validate result structures for all nine required tools
* Full index → search → locate → read → replace cycle against fixture corpus

### Excluded

* Performance benchmarking
* HTTP API
* Embeddings or semantic search
* Multi-user or locking

## Acceptance Criteria

All items from spec §19 must pass:

* A user can index a directory of `.docx`, `.pptx`, and `.xlsx` files from the CLI
* Search returns results in under acceptable local latency for the fixture corpus
* Direct locate works for paragraph, slide text shape, and cell
* Read returns current source content
* Replace and append work for Word paragraphs and PowerPoint text shapes
* Write-cell works for Excel cells
* Every write produces a versioned output file by default
* The changed file is reindexed automatically
* The MCP server exposes equivalent operations as tools
* CLI and MCP both rely on the same underlying services
* All exit codes are correct for success and all defined failure modes
* Writes outside allowed roots are rejected
* `--json` output parses as valid JSON for all commands
