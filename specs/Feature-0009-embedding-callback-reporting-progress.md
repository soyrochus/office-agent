# Feature 0009 — Indexing Progress Reporting

## Goal

Provide real-time visual feedback during `office-agent index` and `office-agent reindex` so the user is never left staring at a silent terminal. The primary pain point is embedding generation, which blocks for seconds-to-minutes with no output. Text-only indexing also gets progress reporting to give a unified, consistent visual experience across both code paths.

---

## Scope

### Included

#### Progress reporter protocol (service layer boundary)

- New `ProgressReporter` protocol in `src/offagent/app/progress.py`
- The protocol is the contract between the service layer (which drives work) and the interface layer (which owns the display)
- `AppServices.index_path` and `AppServices.index_document` gain an optional `reporter: ProgressReporter | None = None` parameter
- The service layer calls reporter methods at well-defined lifecycle points; it never imports `rich` directly
- A `NullProgressReporter` implementation (does nothing) lives alongside the protocol and is the default when no reporter is provided

#### Callback threading into the embedding provider

- `EmbeddingProvider` Protocol gains an optional `on_progress: Callable[[int, int], None] | None = None` parameter on `embed_texts`
- `LocalEmbeddingProvider.embed_texts` accepts and honours this parameter
- `_FastEmbedBackend.embed` is refactored from a list comprehension to an explicit iterator loop so it can fire the callback after each vector is produced
- `_HashingBackend.embed` receives the same treatment for consistency
- The callback signature is `(items_done: int, items_total: int) -> None`; called once per completed item

#### `rich`-based terminal progress display

- Add `rich` as a direct dependency in `pyproject.toml`
- New `RichProgressReporter` class in `src/offagent/interfaces/cli_progress.py`
- Uses a single `rich.progress.Progress` context that spans the entire `index_path` call, showing:
  - A file-level task: `"Indexing  <filename>"` with a spinner and an `n/total` counter
  - An embedding-level sub-task (only shown when embeddings are active): `"Embedding  <n> items"` with a bar and elapsed time
- Visual style: `SpinnerColumn`, `TextColumn` (left-justified file name), `BarColumn` (compact, only when a total is known), `MofNCompleteColumn`, `TimeElapsedColumn`
- Progress renders to `stderr` so that piped or redirected stdout is unaffected
- Progress is suppressed entirely when `--quiet` or `--json` is active (a `NullProgressReporter` is passed instead)

#### CLI wiring

- `index_command` and `reindex_command` in `cli.py` construct the appropriate reporter and pass it to `services.index_path` / `services.reindex_path`
- Reporter construction is gated on `not (quiet or as_json)` and on `sys.stderr.isatty()` — if stderr is not a terminal (e.g. redirected to a log file) a `NullProgressReporter` is used

---

## Module Structure Changes

```
src/offagent/
├── adapters/
│   └── embedding_provider.py   MODIFIED — on_progress param on embed_texts + iterator loop in backends
├── app/
│   ├── progress.py              NEW — ProgressReporter protocol + NullProgressReporter
│   └── services.py              MODIFIED — reporter param on index_path / index_document
└── interfaces/
    ├── cli.py                   MODIFIED — construct reporter, pass to services
    └── cli_progress.py          NEW — RichProgressReporter
```

---

## Protocol Definition

```python
# src/offagent/app/progress.py

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ProgressReporter(Protocol):
    def on_index_start(self, total_files: int) -> None:
        """Called once before the first file is processed."""
        ...

    def on_file_start(self, path: Path, index: int, total: int) -> None:
        """Called when processing of a single file begins."""
        ...

    def on_embedding_start(self, path: Path, item_count: int) -> None:
        """Called immediately before embed_texts() is invoked for a file."""
        ...

    def on_embedding_item(self, done: int, total: int) -> None:
        """Called after each individual embedding vector is produced."""
        ...

    def on_file_done(self, path: Path, items_indexed: int) -> None:
        """Called when a file has been fully processed and committed."""
        ...

    def on_index_done(self, files_indexed: int, files_skipped: int) -> None:
        """Called once after all files have been processed."""
        ...


class NullProgressReporter:
    """No-op reporter used when quiet/json/non-tty output is active."""

    def on_index_start(self, total_files: int) -> None: ...
    def on_file_start(self, path: Path, index: int, total: int) -> None: ...
    def on_embedding_start(self, path: Path, item_count: int) -> None: ...
    def on_embedding_item(self, done: int, total: int) -> None: ...
    def on_file_done(self, path: Path, items_indexed: int) -> None: ...
    def on_index_done(self, files_indexed: int, files_skipped: int) -> None: ...
```

---

## Embedding Provider Changes

```python
# src/offagent/adapters/embedding_provider.py  (signature changes only)

class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed_texts(
        self,
        texts: list[str],
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[bytes]:
        """Return one float32 BLOB per input text.

        If on_progress is provided it is called with (items_done, items_total)
        after each vector is produced, enabling streaming progress reporting.
        """
        ...


class LocalEmbeddingProvider:
    def embed_texts(
        self,
        texts: list[str],
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[bytes]:
        ...  # passes on_progress through to self._backend.embed()


class _FastEmbedBackend:
    def embed(
        self,
        texts: list[str],
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[list[float]]:
        results: list[list[float]] = []
        total = len(texts)
        for i, vector in enumerate(self._model.embed(texts)):
            results.append(list(map(float, vector)))
            if on_progress is not None:
                on_progress(i + 1, total)
        return results
```

The `_HashingBackend` receives identical treatment for consistency, though its loop completes essentially instantly.

---

## Services Layer Changes

```python
# src/offagent/app/services.py  (signatures only)

from offagent.app.progress import NullProgressReporter, ProgressReporter

def index_path(
    self,
    path: Path,
    *,
    with_embeddings: bool = False,
    reporter: ProgressReporter | None = None,
) -> IndexSummary:
    _reporter = reporter or NullProgressReporter()
    # ... existing discovery logic ...
    _reporter.on_index_start(len(candidates))
    for index, candidate in enumerate(candidates):
        _reporter.on_file_start(candidate, index, len(candidates))
        self.index_document(candidate, with_embeddings=with_embeddings, reporter=_reporter)
        _reporter.on_file_done(candidate, items_indexed=...)
    _reporter.on_index_done(files_indexed=indexed, files_skipped=skipped)
    return IndexSummary(...)


def index_document(
    self,
    document_path: Path,
    *,
    with_embeddings: bool = False,
    reporter: ProgressReporter | None = None,
) -> DocumentRef:
    _reporter = reporter or NullProgressReporter()
    # ... existing extraction and store logic ...
    if with_embeddings and items:
        _reporter.on_embedding_start(resolved_path, len(items))
        blobs = provider.embed_texts(
            embedding_texts,
            on_progress=_reporter.on_embedding_item,
        )
    # ...
```

`reindex_path` and `refresh_document` propagate `reporter` to `index_path` / `index_document` with the same optional parameter.

---

## CLI Progress Display

```python
# src/offagent/interfaces/cli_progress.py

from __future__ import annotations

import sys
from pathlib import Path

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)


class RichProgressReporter:
    """Rich-based progress reporter for index / reindex commands."""

    def __init__(self) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(bar_width=24),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=Console(stderr=True),
            transient=True,   # clears on completion, leaving a clean terminal
        )
        self._file_task_id: int | None = None
        self._embed_task_id: int | None = None

    def __enter__(self) -> RichProgressReporter:
        self._progress.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._progress.__exit__(*args)

    def on_index_start(self, total_files: int) -> None:
        self._file_task_id = self._progress.add_task(
            "Indexing", total=total_files
        )

    def on_file_start(self, path: Path, index: int, total: int) -> None:
        self._progress.update(
            self._file_task_id,
            description=f"Indexing  {path.name}",
        )

    def on_embedding_start(self, path: Path, item_count: int) -> None:
        if self._embed_task_id is None:
            self._embed_task_id = self._progress.add_task(
                f"Embedding  {path.name}", total=item_count
            )
        else:
            self._progress.reset(
                self._embed_task_id,
                description=f"Embedding  {path.name}",
                total=item_count,
            )

    def on_embedding_item(self, done: int, total: int) -> None:
        if self._embed_task_id is not None:
            self._progress.update(self._embed_task_id, completed=done)

    def on_file_done(self, path: Path, items_indexed: int) -> None:
        self._progress.advance(self._file_task_id)
        if self._embed_task_id is not None:
            self._progress.update(self._embed_task_id, visible=False)

    def on_index_done(self, files_indexed: int, files_skipped: int) -> None:
        pass  # progress context exit handles cleanup
```

### CLI wiring in `cli.py`

```python
# src/offagent/interfaces/cli.py

def index_command(...) -> None:
    services = AppServices(load_config(config))
    use_progress = not (quiet or as_json) and sys.stderr.isatty()

    if use_progress:
        reporter = RichProgressReporter()
        with reporter:
            summary = services.index_path(path, with_embeddings=with_embeddings, reporter=reporter)
    else:
        summary = services.index_path(path, with_embeddings=with_embeddings)

    _run_command(
        lambda: emit_output(
            {"path": path.resolve(), "summary": summary},
            as_json=as_json,
            quiet=quiet,
            human_renderer=render_index_summary,
            echo=typer.echo,
        ),
        as_json=as_json,
        quiet=quiet,
    )
```

The same pattern applies to `reindex_command`.

---

## Dependency Addition

```toml
# pyproject.toml
rich = ">=13.0"
```

`rich` is the de-facto standard for terminal output in modern Python CLIs and is already a transitive dependency of several popular tools. It provides spinner, bar, elapsed time, and console formatting in a single package without optional extras.

---

## Suppression Rules

| Condition | Reporter used |
|-----------|--------------|
| `--quiet` | `NullProgressReporter` |
| `--json` | `NullProgressReporter` |
| `stderr` is not a TTY | `NullProgressReporter` |
| Normal interactive use | `RichProgressReporter` |

This ensures CI pipelines, piped output, and `--json` consumers never see ANSI escape sequences mixed into their data stream.

---

## Visual Behaviour

When running `office-agent index ./docs --with-embeddings` in an interactive terminal the display shows two concurrent lines, updating in place:

```
⠋ Indexing  quarterly-report.docx    ━━━━━━━━━━━━━━━━━━━━━━━━   2/5  0:00:03
⠹ Embedding quarterly-report.docx   ━━━━━━━━━━━━━━━━━━         84/120  0:00:07
```

- The file task line advances once per completed document.
- The embedding task line is visible only while embeddings are being generated; it disappears (not visible) between files.
- Both lines are `transient=True` and are erased on completion, leaving only the final summary line printed by `render_index_summary`.
- For text-only indexing (no `--with-embeddings`) only the file task line appears, providing the same spinner-based reassurance without a bar.

---

## Acceptance Criteria

- Running `office-agent index ./tests/fixtures --with-embeddings` in a real terminal displays a spinner and a per-item embedding progress bar that advances without gaps or flickering.
- Running the same command with `--quiet` produces no terminal output beyond what `--quiet` already suppresses.
- Running the same command with `--json` produces valid JSON on stdout with no ANSI sequences embedded.
- Running the command with `stderr` redirected to a file (`2>/dev/null`) produces no escape sequences in the file and does not crash.
- Running `office-agent index ./tests/fixtures` (no `--with-embeddings`) shows the file spinner only; no embedding bar appears.
- All existing CLI tests continue to pass without modification.
- The `EmbeddingProvider` Protocol change is backwards-compatible: existing callers that omit `on_progress` are unaffected.
- `NullProgressReporter` satisfies the `ProgressReporter` Protocol (verified by a mypy structural check or a `isinstance` runtime assert in tests).

---

## Architectural Notes

Progress display is a presentation concern that belongs exclusively in the `interfaces` layer. The service layer is aware only of the abstract `ProgressReporter` protocol imported from `app/progress.py` — it never imports `rich` or any other display library. The concrete `RichProgressReporter` lives in `interfaces/cli_progress.py` and is instantiated only in the CLI command functions. This preserves the `interfaces → services → adapters` call direction and keeps the service layer testable without mocking display state.

The `on_progress` callback on `embed_texts` is the minimum seam required to thread real-time progress out of the `_FastEmbedBackend` generator loop. No other layer needs to know about the per-item callback — it is an internal implementation detail of the provider wiring.
