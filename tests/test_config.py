from __future__ import annotations

import os

from offagent.config import load_config


def test_loads_file_and_environment_overrides(tmp_path) -> None:
    config_path = tmp_path / "office-agent.toml"
    config_path.write_text(
        """
[offagent]
index_path = "from-file/index.sqlite3"
document_roots = ["docs", "shared"]
""".strip()
    )

    env = {
        "OFFAGENT_CONFIG": str(config_path),
        "OFFAGENT_INDEX_PATH": str(tmp_path / "from-env" / "index.sqlite3"),
        "OFFAGENT_DOCUMENT_ROOTS": os.pathsep.join(
            [str(tmp_path / "env-docs"), str(tmp_path / "env-shared")]
        ),
    }

    config = load_config(env=env)

    assert config.index_path == tmp_path / "from-env" / "index.sqlite3"
    assert config.document_roots == (tmp_path / "env-docs", tmp_path / "env-shared")
    assert config.config_path == config_path


def test_uses_defaults_when_no_config_is_present() -> None:
    config = load_config(env={})
    assert config.document_roots == ()
    assert str(config.index_path).endswith(".offagent/index.sqlite3")
