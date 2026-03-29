from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Sequence

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

ITEM_EMBEDDINGS_SQL = """
CREATE TABLE IF NOT EXISTS item_embeddings (
    storage_id TEXT PRIMARY KEY REFERENCES items(storage_id),
    model_name TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding BLOB NOT NULL,
    updated_at TEXT NOT NULL
);
"""

XLSX_ROW_EMBEDDINGS_SQL = """
CREATE TABLE IF NOT EXISTS xlsx_row_embeddings (
    embedding_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    row_number INTEGER NOT NULL,
    representative_storage_id TEXT NOT NULL REFERENCES items(storage_id),
    content_text TEXT NOT NULL,
    preview TEXT NOT NULL,
    model_name TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding BLOB NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(document_id, sheet_name, row_number),
    FOREIGN KEY (document_id) REFERENCES documents(document_id)
);
"""

XLSX_ROW_EMBEDDING_CELLS_SQL = """
CREATE TABLE IF NOT EXISTS xlsx_row_embedding_cells (
    embedding_id TEXT NOT NULL REFERENCES xlsx_row_embeddings(embedding_id),
    storage_id TEXT NOT NULL REFERENCES items(storage_id),
    cell_coordinate TEXT NOT NULL,
    cell_order INTEGER NOT NULL,
    is_representative INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (embedding_id, storage_id)
);
"""

EMBEDDING_META_SQL = """
CREATE TABLE IF NOT EXISTS embedding_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

EMBEDDING_META_KEYS = {
    "model_name",
    "dimensions",
    "similarity_metric",
    "schema_version",
}
EMBEDDING_SCHEMA_VERSION = "1"
SIMILARITY_METRIC = "cosine"


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

    connection.executescript(DOCUMENTS_SQL)
    connection.executescript(ITEMS_SQL)
    connection.executescript(ITEM_EMBEDDINGS_SQL)
    connection.executescript(XLSX_ROW_EMBEDDINGS_SQL)
    connection.executescript(XLSX_ROW_EMBEDDING_CELLS_SQL)
    connection.executescript(EMBEDDING_META_SQL)
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


def make_xlsx_row_embedding_id(
    document_id: str, sheet_name: str, row_number: int
) -> str:
    return f"{document_id}:xlsx-row:{sheet_name}!{row_number}"


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


def fetch_document_by_path(
    connection: sqlite3.Connection, document_path: Path
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT d.*, COUNT(i.storage_id) AS item_count
        FROM documents AS d
        LEFT JOIN items AS i ON i.document_id = d.document_id
        WHERE d.path = ? AND d.is_active = 1
        GROUP BY d.document_id
        """,
        (str(document_path.resolve()),),
    ).fetchone()


def fetch_document_by_id(
    connection: sqlite3.Connection, document_id: str
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT d.*, COUNT(i.storage_id) AS item_count
        FROM documents AS d
        LEFT JOIN items AS i ON i.document_id = d.document_id
        WHERE d.document_id = ? AND d.is_active = 1
        GROUP BY d.document_id
        """,
        (document_id,),
    ).fetchone()


def fetch_documents(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT d.*, COUNT(i.storage_id) AS item_count
            FROM documents AS d
            LEFT JOIN items AS i ON i.document_id = d.document_id
            WHERE d.is_active = 1
            GROUP BY d.document_id
            ORDER BY d.path
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
        i.storage_id,
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


def fetch_item_embeddings(
    connection: sqlite3.Connection,
    *,
    file_type: str | None = None,
    document_path: Path | None = None,
) -> list[sqlite3.Row]:
    sql = """
    SELECT
        e.storage_id,
        e.model_name,
        e.dimensions,
        e.embedding,
        e.updated_at,
        i.document_id,
        i.item_id,
        i.item_type,
        i.locator,
        i.preview,
        i.content_text,
        i.metadata_json,
        d.path,
        d.display_name
    FROM item_embeddings AS e
    JOIN items AS i ON i.storage_id = e.storage_id
    JOIN documents AS d ON d.document_id = i.document_id
    WHERE d.is_active = 1
    """
    params: list[object] = []

    if file_type is not None:
        sql += " AND d.file_type = ?"
        params.append(file_type)

    if document_path is not None:
        sql += " AND d.path = ?"
        params.append(str(document_path.resolve()))

    sql += " ORDER BY d.path, i.item_id"
    return list(connection.execute(sql, params).fetchall())


def fetch_xlsx_row_embeddings(
    connection: sqlite3.Connection,
    *,
    file_type: str | None = None,
    document_path: Path | None = None,
) -> list[sqlite3.Row]:
    if file_type not in (None, "xlsx"):
        return []

    sql = """
    SELECT
        e.embedding_id,
        e.document_id,
        e.sheet_name,
        e.row_number,
        e.representative_storage_id,
        e.content_text,
        e.preview AS row_preview,
        e.model_name,
        e.dimensions,
        e.embedding,
        e.updated_at,
        i.item_id,
        i.item_type,
        i.locator,
        i.preview,
        i.content_text AS item_content_text,
        i.metadata_json,
        d.path,
        d.display_name
    FROM xlsx_row_embeddings AS e
    JOIN documents AS d ON d.document_id = e.document_id
    JOIN items AS i ON i.storage_id = e.representative_storage_id
    WHERE d.is_active = 1
      AND d.file_type = 'xlsx'
    """
    params: list[object] = []

    if document_path is not None:
        sql += " AND d.path = ?"
        params.append(str(document_path.resolve()))

    sql += " ORDER BY d.path, e.sheet_name, e.row_number"
    return list(connection.execute(sql, params).fetchall())


def fetch_xlsx_row_embedding_cells(
    connection: sqlite3.Connection,
    embedding_id: str,
) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT
                embedding_id,
                storage_id,
                cell_coordinate,
                cell_order,
                is_representative
            FROM xlsx_row_embedding_cells
            WHERE embedding_id = ?
            ORDER BY cell_order, cell_coordinate
            """,
            (embedding_id,),
        ).fetchall()
    )


def has_item_embeddings(
    connection: sqlite3.Connection,
    *,
    file_type: str | None = None,
    document_path: Path | None = None,
) -> bool:
    if file_type == "xlsx":
        sql = """
        SELECT 1
        FROM xlsx_row_embeddings AS e
        JOIN documents AS d ON d.document_id = e.document_id
        WHERE d.is_active = 1
          AND d.file_type = 'xlsx'
        """
        params: list[object] = []
        if document_path is not None:
            sql += " AND d.path = ?"
            params.append(str(document_path.resolve()))
        sql += " LIMIT 1"
        return connection.execute(sql, params).fetchone() is not None

    if file_type is None:
        if has_item_embeddings(
            connection, file_type="docx", document_path=document_path
        ):
            return True
        if has_item_embeddings(
            connection, file_type="pptx", document_path=document_path
        ):
            return True
        return has_item_embeddings(
            connection, file_type="xlsx", document_path=document_path
        )

    sql = """
    SELECT 1
    FROM item_embeddings AS e
    JOIN items AS i ON i.storage_id = e.storage_id
    JOIN documents AS d ON d.document_id = i.document_id
    WHERE d.is_active = 1
    """
    params: list[object] = []

    if file_type is not None:
        sql += " AND d.file_type = ?"
        params.append(file_type)

    if document_path is not None:
        sql += " AND d.path = ?"
        params.append(str(document_path.resolve()))

    sql += " LIMIT 1"
    return connection.execute(sql, params).fetchone() is not None


def delete_document_embeddings(
    connection: sqlite3.Connection, document_id: str
) -> None:
    delete_document_xlsx_row_embeddings(connection, document_id)
    connection.execute(
        """
        DELETE FROM item_embeddings
        WHERE storage_id LIKE ?
        """,
        (f"{document_id}:%",),
    )


def delete_document_xlsx_row_embeddings(
    connection: sqlite3.Connection, document_id: str
) -> None:
    connection.execute(
        """
        DELETE FROM xlsx_row_embedding_cells
        WHERE embedding_id IN (
            SELECT embedding_id
            FROM xlsx_row_embeddings
            WHERE document_id = ?
        )
        """,
        (document_id,),
    )
    connection.execute(
        """
        DELETE FROM xlsx_row_embeddings
        WHERE document_id = ?
        """,
        (document_id,),
    )


def replace_document_embeddings(
    connection: sqlite3.Connection,
    *,
    document_id: str,
    model_name: str,
    dimensions: int,
    embeddings: Sequence[tuple[str, bytes]],
) -> None:
    delete_document_embeddings(connection, document_id)
    updated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    for storage_id, embedding in embeddings:
        connection.execute(
            """
            INSERT INTO item_embeddings (
                storage_id,
                model_name,
                dimensions,
                embedding,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (storage_id, model_name, dimensions, embedding, updated_at),
        )


def replace_xlsx_row_embeddings(
    connection: sqlite3.Connection,
    *,
    document_id: str,
    model_name: str,
    dimensions: int,
    row_embeddings: Sequence[
        tuple[
            str,
            str,
            int,
            str,
            str,
            str,
            bytes,
            Sequence[tuple[str, str, int, bool]],
        ]
    ],
) -> None:
    delete_document_xlsx_row_embeddings(connection, document_id)
    updated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    for (
        embedding_id,
        sheet_name,
        row_number,
        representative_storage_id,
        content_text,
        preview,
        embedding,
        contributing_cells,
    ) in row_embeddings:
        connection.execute(
            """
            INSERT INTO xlsx_row_embeddings (
                embedding_id,
                document_id,
                sheet_name,
                row_number,
                representative_storage_id,
                content_text,
                preview,
                model_name,
                dimensions,
                embedding,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                embedding_id,
                document_id,
                sheet_name,
                row_number,
                representative_storage_id,
                content_text,
                preview,
                model_name,
                dimensions,
                embedding,
                updated_at,
            ),
        )
        for (
            storage_id,
            cell_coordinate,
            cell_order,
            is_representative,
        ) in contributing_cells:
            connection.execute(
                """
                INSERT INTO xlsx_row_embedding_cells (
                    embedding_id,
                    storage_id,
                    cell_coordinate,
                    cell_order,
                    is_representative
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    embedding_id,
                    storage_id,
                    cell_coordinate,
                    cell_order,
                    1 if is_representative else 0,
                ),
            )


def fetch_embedding_meta(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        row["key"]: row["value"]
        for row in connection.execute(
            """
            SELECT key, value
            FROM embedding_meta
            """
        ).fetchall()
    }


def ensure_embedding_meta(
    connection: sqlite3.Connection,
    *,
    model_name: str,
    dimensions: int,
) -> None:
    expected = {
        "model_name": model_name,
        "dimensions": str(dimensions),
        "similarity_metric": SIMILARITY_METRIC,
        "schema_version": EMBEDDING_SCHEMA_VERSION,
    }
    existing = fetch_embedding_meta(connection)

    if not existing:
        for key, value in expected.items():
            connection.execute(
                """
                INSERT INTO embedding_meta (key, value)
                VALUES (?, ?)
                """,
                (key, value),
            )
        return

    if set(existing) != EMBEDDING_META_KEYS:
        raise RuntimeError("Stored embedding metadata is incomplete or unsupported.")

    for key, expected_value in expected.items():
        actual_value = existing.get(key)
        if actual_value != expected_value:
            raise RuntimeError(
                f"Embedding metadata mismatch for {key}: expected {expected_value}, found {actual_value}."
            )


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
