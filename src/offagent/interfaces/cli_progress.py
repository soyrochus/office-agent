from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)


class RichProgressReporter:
    """Rich-based progress reporter for index and reindex commands."""

    def __init__(
        self, *, console: Console | None = None, transient: bool = True
    ) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(bar_width=24),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console or Console(stderr=True),
            transient=transient,
        )
        self._file_task_id: int | None = None
        self._embed_task_id: int | None = None
        self._current_file_index = 0

    def __enter__(self) -> "RichProgressReporter":
        self._progress.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._progress.__exit__(*args)

    def on_index_start(self, total_files: int) -> None:
        self._file_task_id = self._progress.add_task(
            "Indexing", total=total_files, completed=0
        )

    def on_file_start(self, path: Path, index: int, total: int) -> None:
        self._current_file_index = index
        self._hide_embedding_task()
        if self._file_task_id is None:
            self._file_task_id = self._progress.add_task(
                f"Indexing {path.name}",
                total=total,
                completed=max(index - 1, 0),
            )
            return
        self._progress.update(
            self._file_task_id,
            description=f"Indexing {path.name}",
            total=total,
            completed=max(index - 1, 0),
            visible=True,
        )

    def on_embedding_start(self, path: Path, item_count: int) -> None:
        if item_count <= 0:
            self._hide_embedding_task()
            return
        description = f"Embedding {item_count} items"
        if self._embed_task_id is None:
            self._embed_task_id = self._progress.add_task(
                description, total=item_count, completed=0
            )
            return
        self._progress.update(
            self._embed_task_id,
            description=description,
            total=item_count,
            completed=0,
            visible=True,
        )

    def on_embedding_item(self, done: int, total: int) -> None:
        if self._embed_task_id is None:
            self._embed_task_id = self._progress.add_task(
                f"Embedding {total} items",
                total=total,
                completed=done,
            )
            return
        self._progress.update(
            self._embed_task_id,
            description=f"Embedding {total} items",
            total=total,
            completed=done,
            visible=True,
        )

    def on_file_done(self, path: Path, items_indexed: int) -> None:
        if self._file_task_id is not None:
            self._progress.update(
                self._file_task_id,
                description=f"Indexing {path.name}",
                completed=self._current_file_index,
            )
        self._hide_embedding_task()

    def on_index_done(self, files_indexed: int, files_skipped: int) -> None:
        self._hide_embedding_task()
        if self._file_task_id is not None:
            self._progress.update(
                self._file_task_id,
                description="Indexing complete",
                completed=files_indexed + files_skipped,
            )

    def _hide_embedding_task(self) -> None:
        if self._embed_task_id is None:
            return
        self._progress.update(self._embed_task_id, visible=False)
