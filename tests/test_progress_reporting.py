from __future__ import annotations

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from offagent.adapters.embedding_provider import LocalEmbeddingProvider
from offagent.app.progress import NullProgressReporter
from offagent.app.services import AppServices
from offagent.config import AppConfig
from offagent.interfaces import cli as cli_module


def _vector_config(tmp_path) -> AppConfig:
    return AppConfig(
        index_path=tmp_path / "state" / "index.sqlite3",
        document_roots=(tmp_path,),
        embedding_model="hash://progress",
        embedding_dimensions=32,
        vector_search_top_k=10,
    )


class RecordingReporter:
    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []

    def __enter__(self) -> "RecordingReporter":
        self.events.append(("enter",))
        return self

    def __exit__(self, *args: object) -> None:
        self.events.append(("exit",))

    def on_index_start(self, total_files: int) -> None:
        self.events.append(("index_start", total_files))

    def on_file_start(self, path: Path, index: int, total: int) -> None:
        self.events.append(("file_start", path.resolve(), index, total))

    def on_embedding_start(self, path: Path, item_count: int) -> None:
        self.events.append(("embedding_start", path.resolve(), item_count))

    def on_embedding_item(self, done: int, total: int) -> None:
        self.events.append(("embedding_item", done, total))

    def on_file_done(self, path: Path, items_indexed: int) -> None:
        self.events.append(("file_done", path.resolve(), items_indexed))

    def on_index_done(self, files_indexed: int, files_skipped: int) -> None:
        self.events.append(("index_done", files_indexed, files_skipped))


def test_local_embedding_provider_reports_progress() -> None:
    provider = LocalEmbeddingProvider(model_name="hash://unit-test", dimensions=24)
    calls: list[tuple[int, int]] = []

    blobs = provider.embed_texts(
        [
            "Supplier shall review variance.",
            "Follow up with finance.",
            "Prepare next update.",
        ],
        on_progress=lambda done, total: calls.append((done, total)),
    )

    assert len(blobs) == 3
    assert calls == [(1, 3), (2, 3), (3, 3)]


def test_index_path_reports_progress_events_for_embeddings(sample_docx, tmp_path) -> None:
    services = AppServices(_vector_config(tmp_path))
    reporter = RecordingReporter()

    summary = services.index_path(sample_docx, with_embeddings=True, reporter=reporter)

    assert summary.files_scanned == 1
    assert summary.files_indexed == 1
    assert summary.files_skipped == 0
    assert reporter.events == [
        ("index_start", 1),
        ("file_start", sample_docx.resolve(), 1, 1),
        ("embedding_start", sample_docx.resolve(), 4),
        ("embedding_item", 1, 4),
        ("embedding_item", 2, 4),
        ("embedding_item", 3, 4),
        ("embedding_item", 4, 4),
        ("file_done", sample_docx.resolve(), 4),
        ("index_done", 1, 0),
    ]


def test_index_path_accepts_null_reporter_without_changing_results(sample_docx, tmp_path) -> None:
    services = AppServices(_vector_config(tmp_path))

    summary = services.index_path(
        sample_docx,
        with_embeddings=True,
        reporter=NullProgressReporter(),
    )

    connection = sqlite3.connect(tmp_path / "state" / "index.sqlite3")
    try:
        row_count = connection.execute("SELECT COUNT(*) FROM item_embeddings").fetchone()[0]
    finally:
        connection.close()

    assert summary.files_indexed == 1
    assert row_count == 4


def test_build_index_reporter_suppresses_progress_when_requested(monkeypatch) -> None:
    monkeypatch.setattr(cli_module, "_stderr_supports_live_progress", lambda: True)

    assert isinstance(cli_module._build_index_reporter(as_json=True, quiet=False), NullProgressReporter)
    assert isinstance(cli_module._build_index_reporter(as_json=False, quiet=True), NullProgressReporter)

    monkeypatch.setattr(cli_module, "_stderr_supports_live_progress", lambda: False)
    assert isinstance(cli_module._build_index_reporter(as_json=False, quiet=False), NullProgressReporter)


def test_index_command_uses_reporter_for_interactive_runs(
    monkeypatch,
    sample_docx,
    config_path,
) -> None:
    reporter = RecordingReporter()
    monkeypatch.setattr(cli_module, "_build_index_reporter", lambda *, as_json, quiet: reporter)

    result = CliRunner().invoke(
        cli_module.build_app(),
        ["index", str(sample_docx), "--with-embeddings", "--config", str(config_path)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "files_indexed=1" in result.output
    assert reporter.events[0] == ("enter",)
    assert ("embedding_start", sample_docx.resolve(), 4) in reporter.events
    assert reporter.events[-1] == ("exit",)
