from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_cli(config_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "offagent",
            *args,
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_vector_modes_and_exit_codes(golden_config_path, golden_workspace) -> None:
    docs_dir = golden_workspace / "docs"

    indexed = _run_cli(golden_config_path, "index", str(docs_dir), "--with-embeddings")
    semantic = _run_cli(
        golden_config_path,
        "search",
        "supplier shall",
        "--type",
        "docx",
        "--mode",
        "semantic",
        "--json",
    )
    hybrid = _run_cli(
        golden_config_path,
        "search",
        "supplier shall",
        "--type",
        "docx",
        "--mode",
        "hybrid",
        "--json",
    )
    invalid_mode = _run_cli(
        golden_config_path,
        "search",
        "supplier shall",
        "--mode",
        "invalid",
    )

    semantic_payload = json.loads(semantic.stdout)
    hybrid_payload = json.loads(hybrid.stdout)

    assert indexed.returncode == 0, indexed.stderr
    assert semantic.returncode == 0, semantic.stderr
    assert semantic_payload["hits"][0]["match_mode"] == "semantic"
    assert semantic_payload["hits"][0]["scores"]["semantic"] >= 0.0
    assert hybrid.returncode == 0, hybrid.stderr
    assert hybrid_payload["hits"][0]["match_mode"] == "hybrid"
    assert "final" in hybrid_payload["hits"][0]["scores"]
    assert invalid_mode.returncode == 2


def test_cli_semantic_search_without_embeddings_exits_three(golden_config_path, golden_workspace) -> None:
    docs_dir = golden_workspace / "docs"
    _run_cli(golden_config_path, "index", str(docs_dir))

    semantic = _run_cli(
        golden_config_path,
        "search",
        "supplier shall",
        "--type",
        "docx",
        "--mode",
        "semantic",
    )

    assert semantic.returncode == 3
    assert "No embeddings are indexed" in semantic.stderr
