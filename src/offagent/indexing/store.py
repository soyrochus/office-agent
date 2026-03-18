from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    file_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    modified_time REAL NOT NULL,
    content_hash TEXT
);

CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    locator TEXT NOT NULL,
    preview TEXT NOT NULL,
    content_text TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
    item_id UNINDEXED,
    document_id UNINDEXED,
    content_text
);
"""


class StoreCapabilityError(RuntimeError):
    """Raised when the runtime cannot satisfy store requirements."""


def connect(index_path: Path) -> sqlite3.Connection:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(index_path)
    connection.row_factory = sqlite3.Row
    return connection


def supports_fts5(connection: sqlite3.Connection) -> bool:
    table_name = "fts5_probe"
    try:
        connection.execute(
            f"CREATE VIRTUAL TABLE {table_name} USING fts5(content_text)"
        )
        connection.execute(f"DROP TABLE {table_name}")
        return True
    except sqlite3.OperationalError:
        return False


def initialize_schema(connection: sqlite3.Connection) -> None:
    if not supports_fts5(connection):
        raise StoreCapabilityError("SQLite FTS5 support is required.")

    connection.executescript(SCHEMA_SQL)
    connection.commit()


def ensure_ready(index_path: Path) -> sqlite3.Connection:
    connection = connect(index_path)
    try:
        initialize_schema(connection)
    except Exception:
        connection.close()
        raise
    return connection
