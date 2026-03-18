from __future__ import annotations

import subprocess
import sys

from docx import Document


def _run_cli(config_path, *args: str) -> subprocess.CompletedProcess[str]:
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


def test_docx_cli_round_trip(sample_docx, config_path) -> None:
    index_result = _run_cli(config_path, "index", str(sample_docx))
    search_result = _run_cli(config_path, "search", "Supplier shall", "--type", "docx")
    locate_result = _run_cli(config_path, "locate", "--doc", str(sample_docx), "--paragraph", "3")
    read_result = _run_cli(config_path, "read", "--doc", str(sample_docx), "--item", "para:3")
    replace_result = _run_cli(
        config_path,
        "replace",
        "--doc",
        str(sample_docx),
        "--item",
        "para:1",
        "--text",
        "CLI replaced text.",
    )
    append_result = _run_cli(
        config_path,
        "append",
        "--doc",
        str(sample_docx),
        "--item",
        "para:2",
        "--text",
        "CLI append text.",
    )

    assert index_result.returncode == 0, index_result.stderr
    assert "indexed 1" in index_result.stdout
    assert search_result.returncode == 0, search_result.stderr
    assert "para:3" in search_result.stdout
    assert locate_result.returncode == 0, locate_result.stderr
    assert "para:3" in locate_result.stdout
    assert read_result.returncode == 0, read_result.stderr
    assert "Supplier shall deliver by Friday." in read_result.stdout
    assert replace_result.returncode == 0, replace_result.stderr
    assert append_result.returncode == 0, append_result.stderr

    document = Document(str(sample_docx))
    assert document.paragraphs[1].text == "CLI replaced text."
    assert document.paragraphs[1].runs[0].bold is True
    assert document.paragraphs[2].text == "CLI append text."
