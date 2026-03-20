from __future__ import annotations

import os
from pathlib import Path

from offagent.config import load_config


def test_loads_file_and_environment_overrides(tmp_path) -> None:
    config_path = tmp_path / "office-agent.toml"
    config_path.write_text(
        """
[offagent]
index_path = "from-file/index.sqlite3"
document_roots = ["docs", "shared"]
allowed_roots = ["allowed-file"]
output_directory = "from-file/edited"
output_roots = ["outputs-file"]
allow_inplace_overwrite = false
embedding_model = "hash://file"
embedding_dimensions = 96
vector_search_top_k = 33
hybrid_keyword_weight = 0.25
hybrid_semantic_weight = 0.75
""".strip()
    )

    env = {
        "OFFAGENT_CONFIG": str(config_path),
        "OFFAGENT_INDEX_PATH": str(tmp_path / "from-env" / "index.sqlite3"),
        "OFFAGENT_DOCUMENT_ROOTS": os.pathsep.join(
            [str(tmp_path / "env-docs"), str(tmp_path / "env-shared")]
        ),
        "OFFAGENT_ALLOWED_ROOTS": os.pathsep.join(
            [str(tmp_path / "env-allowed"), str(tmp_path / "env-shared")]
        ),
        "OFFAGENT_OUTPUT_DIRECTORY": str(tmp_path / "from-env" / "edited"),
        "OFFAGENT_OUTPUT_ROOTS": os.pathsep.join(
            [str(tmp_path / "env-output"), str(tmp_path / "from-env" / "edited")]
        ),
        "OFFAGENT_ALLOW_INPLACE_OVERWRITE": "true",
        "OFFAGENT_EMBEDDING_MODEL": "hash://env",
        "OFFAGENT_EMBEDDING_DIMENSIONS": "64",
        "OFFAGENT_VECTOR_SEARCH_TOP_K": "27",
        "OFFAGENT_HYBRID_KEYWORD_WEIGHT": "0.6",
        "OFFAGENT_HYBRID_SEMANTIC_WEIGHT": "0.4",
    }

    config = load_config(env=env)

    assert config.index_path == tmp_path / "from-env" / "index.sqlite3"
    assert config.document_roots == (tmp_path / "env-docs", tmp_path / "env-shared")
    assert config.allowed_roots == (tmp_path / "env-allowed", tmp_path / "env-shared")
    assert config.output_directory == tmp_path / "from-env" / "edited"
    assert config.output_roots == (tmp_path / "env-output", tmp_path / "from-env" / "edited")
    assert config.allow_inplace_overwrite is True
    assert config.embedding_model == "hash://env"
    assert config.embedding_dimensions == 64
    assert config.vector_search_top_k == 27
    assert config.hybrid_keyword_weight == 0.6
    assert config.hybrid_semantic_weight == 0.4
    assert config.config_path == config_path


def test_uses_defaults_when_no_config_is_present() -> None:
    config = load_config(env={})
    assert config.document_roots == ()
    assert config.allowed_roots == ()
    assert str(config.index_path).endswith(".offagent/index.sqlite3")
    assert config.output_directory is None
    assert config.output_roots == ()
    assert config.allow_inplace_overwrite is False
    assert config.embedding_model == "BAAI/bge-small-en-v1.5"
    assert config.embedding_dimensions == 384
    assert config.vector_search_top_k == 20
    assert config.hybrid_keyword_weight == 0.4
    assert config.hybrid_semantic_weight == 0.6


def test_output_roots_default_to_output_directory_when_not_explicit(tmp_path) -> None:
    config_path = tmp_path / "office-agent.toml"
    config_path.write_text(
        """
[offagent]
output_directory = "edited"
embedding_model = "hash://file"
""".strip()
    )

    config = load_config(config_path, env={})

    assert config.output_directory == Path("edited")
    assert config.output_roots == (Path("edited"),)
    assert config.embedding_model == "hash://file"
