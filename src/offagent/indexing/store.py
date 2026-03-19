from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, Sequence

from offagent.domain.models import DocumentRef, IndexedItem

DOCUMENTS_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    file_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    modified_time REAL NOT NULL,
    content_hash TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);
"""

ITEMS_SQL = """
CREATE TABLE IF NOT EXISTS items (
    storage_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    locator TEXT NOT NULL,
    preview TEXT NOT NULL,
    content_text TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(document_id, item_id),
    FOREIGN KEY (document_id) REFERENCES documents(document_id)
);
"""

ITEMS_FTS_SQL = """
CREATE VIRTUAL TABLE items_fts USING fts5(
    storage_id UNINDEXED,
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
        connection.execute(f"CREATE VIRTUAL TABLE {table_name} USING fts5(content_text)")
        connection.execute(f"DROP TABLE {table_name}")
        return True
    except sqlite3.OperationalError:
        return False


def initialize_schema(connection: sqlite3.Connection) -> None:
    if not supports_fts5(connection):
        raise StoreCapabilityError("SQLite FTS5 support is required.")

    connection.executescript(DOCUMENTS_SQL)
    connection.executescript(ITEMS_SQL)
    _migrate_documents_table(connection)
    _migrate_items_table(connection)
    _rebuild_items_fts(connection)
    connection.commit()


def ensure_ready(index_path: Path) -> sqlite3.Connection:
    connection = connect(index_path)
    try:
        initialize_schema(connection)
    except Exception:
        connection.close()
        raise
    return connection


def make_storage_id(document_id: str, item_id: str) -> str:
    return f"{document_id}:{item_id}"


def upsert_document(connection: sqlite3.Connection, document: DocumentRef) -> None:
    connection.execute(
        """
        INSERT INTO documents (
            document_id,
            path,
            file_type,
            display_name,
            modified_time,
            content_hash,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(document_id) DO UPDATE SET
            path = excluded.path,
            file_type = excluded.file_type,
            display_name = excluded.display_name,
            modified_time = excluded.modified_time,
            content_hash = excluded.content_hash,
            is_active = 1
        """,
        (
            document.document_id,
            str(document.path),
            document.file_type,
            document.display_name,
            document.modified_time,
            document.content_hash,
        ),
    )


def replace_document_items(
    connection: sqlite3.Connection,
    document_id: str,
    items: Sequence[IndexedItem],
) -> None:
    connection.execute("DELETE FROM items WHERE document_id = ?", (document_id,))
    connection.execute("DELETE FROM items_fts WHERE document_id = ?", (document_id,))

    for item in items:
        storage_id = make_storage_id(document_id, item.item_id)
        connection.execute(
            """
            INSERT INTO items (
                storage_id,
                document_id,
                item_id,
                item_type,
                locator,
                preview,
                content_text,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                storage_id,
                document_id,
                item.item_id,
                item.item_type,
                item.locator,
                item.preview,
                item.content_text,
                json.dumps(item.metadata, sort_keys=True),
            ),
        )
        connection.execute(
            """
            INSERT INTO items_fts (
                storage_id,
                item_id,
                document_id,
                content_text
            )
            VALUES (?, ?, ?, ?)
            """,
            (storage_id, item.item_id, document_id, item.content_text),
        )

    connection.commit()


def fetch_document_by_path(connection: sqlite3.Connection, document_path: Path) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM documents
        WHERE path = ? AND is_active = 1
        """,
        (str(document_path.resolve()),),
    ).fetchone()


def fetch_document_by_id(connection: sqlite3.Connection, document_id: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM documents
        WHERE document_id = ? AND is_active = 1
        """,
        (document_id,),
    ).fetchone()


def fetch_documents(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT *
            FROM documents
            WHERE is_active = 1
            ORDER BY path
            """
        ).fetchall()
    )


def fetch_item_by_id(
    connection: sqlite3.Connection,
    document_id: str,
    item_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM items
        WHERE document_id = ? AND item_id = ?
        """,
        (document_id, item_id),
    ).fetchone()


def fetch_items_for_document(
    connection: sqlite3.Connection,
    document_id: str,
) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT *
            FROM items
            WHERE document_id = ?
            ORDER BY item_id
            """,
            (document_id,),
        ).fetchall()
    )


def search_items(
    connection: sqlite3.Connection,
    query: str,
    *,
    file_type: str | None = None,
    document_path: Path | None = None,
    limit: int = 20,
) -> list[sqlite3.Row]:
    sql = """
    SELECT
        i.document_id,
        i.item_id,
        i.item_type,
        i.locator,
        i.preview,
        i.content_text,
        i.metadata_json,
        d.path,
        d.display_name,
        bm25(items_fts) AS score
    FROM items_fts
    JOIN items AS i ON i.storage_id = items_fts.storage_id
    JOIN documents AS d ON d.document_id = i.document_id
    WHERE items_fts MATCH ?
      AND d.is_active = 1
    """
    params: list[object] = [query]

    if file_type is not None:
        sql += " AND d.file_type = ?"
        params.append(file_type)

    if document_path is not None:
        sql += " AND d.path = ?"
        params.append(str(document_path.resolve()))

    sql += " ORDER BY score, d.path, i.item_id LIMIT ?"
    params.append(limit)

    return list(connection.execute(sql, params).fetchall())


def _migrate_documents_table(connection: sqlite3.Connection) -> None:
    document_columns = _table_columns(connection, "documents")
    if "is_active" not in document_columns:
        connection.execute(
            "ALTER TABLE documents ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
        )


def _migrate_items_table(connection: sqlite3.Connection) -> None:
    item_columns = _table_columns(connection, "items")
    required_columns = {
        "storage_id",
        "document_id",
        "item_id",
        "item_type",
        "locator",
        "preview",
        "content_text",
        "metadata_json",
    }
    if required_columns.issubset(item_columns):
        return

    if item_columns:
        connection.execute("ALTER TABLE items RENAME TO items_legacy")
        connection.executescript(ITEMS_SQL)
        legacy_columns = _table_columns(connection, "items_legacy")
        metadata_expr = "metadata_json" if "metadata_json" in legacy_columns else "'{}'"
        connection.execute(
            f"""
            INSERT INTO items (
                storage_id,
                document_id,
                item_id,
                item_type,
                locator,
                preview,
                content_text,
                metadata_json
            )
            SELECT
                document_id || ':' || item_id,
                document_id,
                item_id,
                item_type,
                locator,
                preview,
                content_text,
                {metadata_expr}
            FROM items_legacy
            """
        )
        connection.execute("DROP TABLE items_legacy")


def _rebuild_items_fts(connection: sqlite3.Connection) -> None:
    connection.execute("DROP TABLE IF EXISTS items_fts")
    connection.executescript(ITEMS_FTS_SQL)
    connection.execute(
        """
        INSERT INTO items_fts (storage_id, item_id, document_id, content_text)
        SELECT storage_id, item_id, document_id, content_text
        FROM items
        """
    )


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}
