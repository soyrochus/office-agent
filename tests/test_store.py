from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from offagent.indexing import store


class StoreTests(unittest.TestCase):
    def test_ensure_ready_creates_expected_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "index.sqlite3"
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

            self.assertIn("documents", table_names)
            self.assertIn("items", table_names)
            self.assertIn("items_fts", table_names)

    def test_initialize_schema_raises_without_fts5_support(self) -> None:
        connection = sqlite3.connect(":memory:")
        try:
            with mock.patch(
                "offagent.indexing.store.supports_fts5",
                return_value=False,
            ):
                with self.assertRaises(store.StoreCapabilityError):
                    store.initialize_schema(connection)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
