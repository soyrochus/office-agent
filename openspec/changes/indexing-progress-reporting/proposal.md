## Why

`office-agent index` and `office-agent reindex` can spend seconds or minutes generating embeddings without emitting any visible progress, which leaves users staring at a silent terminal and unsure whether work is still advancing. This change adds explicit progress reporting so long-running indexing flows stay observable while preserving the existing quiet and JSON output contracts.

## What Changes

- Add real-time terminal progress reporting for `office-agent index` and `office-agent reindex`, including per-file progress and embedding-item progress when embeddings are enabled.
- Introduce a service-layer progress reporting contract so indexing code can report lifecycle events without depending on terminal UI libraries.
- Thread an optional embedding progress callback through embedding provider interfaces and implementations so embedding generation can surface item-by-item progress.
- Add a Rich-based CLI progress reporter that writes to `stderr` and is automatically suppressed for `--quiet`, `--json`, and non-interactive stderr.

## Capabilities

### New Capabilities
- `indexing-progress-reporting`: Defines observable progress behavior for indexing and reindexing workflows, including file-level and embedding-level reporting.

### Modified Capabilities
- `cli-output-modes`: Clarify that progress rendering is non-stdout CLI feedback, must not appear in `--json` output, and must be suppressed when `--quiet` is requested.

## Impact

- Affected code: `src/offagent/app/services.py`, `src/offagent/adapters/embedding_provider.py`, `src/offagent/interfaces/cli.py`
- New modules: `src/offagent/app/progress.py`, `src/offagent/interfaces/cli_progress.py`
- Dependencies: add direct dependency on `rich`
- Systems: indexing and reindex CLI workflows, embedding backends, terminal output behavior
