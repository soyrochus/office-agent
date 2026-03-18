from __future__ import annotations

import sqlite3

import pytest

from offagent.indexing import store


def test_ensure_ready_creates_expected_schema(tmp_path) -> None:
    index_path = tmp_path / "index.sqlite3"
    connection = store.ensure_ready(index_path)
    try:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
    finally:
        connection.close()

    assert "documents" in table_names
    assert "items" in table_names
    assert "items_fts" in table_names


def test_initialize_schema_raises_without_fts5_support(monkeypatch) -> None:
    connection = sqlite3.connect(":memory:")
    try:
        monkeypatch.setattr("offagent.indexing.store.supports_fts5", lambda _: False)
        with pytest.raises(store.StoreCapabilityError):
            store.initialize_schema(connection)
    finally:
        connection.close()
