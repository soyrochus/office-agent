from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from offagent.config import load_config


class ConfigTests(unittest.TestCase):
    def test_loads_file_and_environment_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "office-agent.toml"
            config_path.write_text(
                """
[offagent]
index_path = "from-file/index.sqlite3"
document_roots = ["docs", "shared"]
""".strip()
            )

            env = {
                "OFFAGENT_CONFIG": str(config_path),
                "OFFAGENT_INDEX_PATH": str(temp_path / "from-env" / "index.sqlite3"),
                "OFFAGENT_DOCUMENT_ROOTS": os.pathsep.join(
                    [str(temp_path / "env-docs"), str(temp_path / "env-shared")]
                ),
            }

            config = load_config(env=env)

            self.assertEqual(config.index_path, temp_path / "from-env" / "index.sqlite3")
            self.assertEqual(
                config.document_roots,
                (temp_path / "env-docs", temp_path / "env-shared"),
            )
            self.assertEqual(config.config_path, config_path)

    def test_uses_defaults_when_no_config_is_present(self) -> None:
        config = load_config(env={})
        self.assertEqual(config.document_roots, ())
        self.assertTrue(str(config.index_path).endswith(".offagent/index.sqlite3"))


if __name__ == "__main__":
    unittest.main()
