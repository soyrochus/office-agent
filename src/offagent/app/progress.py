from __future__ import annotations

from pathlib import Path
from typing import Protocol, Self


class ProgressReporter(Protocol):
    def on_index_start(self, total_files: int) -> None:
        """Called once before the first file is processed."""

    def on_file_start(self, path: Path, index: int, total: int) -> None:
        """Called when processing of a single file begins."""

    def on_embedding_start(self, path: Path, item_count: int) -> None:
        """Called immediately before embedding generation starts for a file."""

    def on_embedding_item(self, done: int, total: int) -> None:
        """Called after each embedding vector is produced."""

    def on_file_done(self, path: Path, items_indexed: int) -> None:
        """Called after a file has been fully processed and committed."""

    def on_index_done(self, files_indexed: int, files_skipped: int) -> None:
        """Called once after all files have been processed."""


class NullProgressReporter:
    """No-op reporter used when live progress is suppressed."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def on_index_start(self, total_files: int) -> None:
        return None

    def on_file_start(self, path: Path, index: int, total: int) -> None:
        return None

    def on_embedding_start(self, path: Path, item_count: int) -> None:
        return None

    def on_embedding_item(self, done: int, total: int) -> None:
        return None

    def on_file_done(self, path: Path, items_indexed: int) -> None:
        return None

    def on_index_done(self, files_indexed: int, files_skipped: int) -> None:
        return None
