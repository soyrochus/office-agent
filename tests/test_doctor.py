from __future__ import annotations

import subprocess
import sys

from offagent.app.services import AppServices, format_doctor_report
from offagent.config import AppConfig


def test_doctor_reports_pass_for_bootstrap_checks(tmp_path) -> None:
    document_root = tmp_path / "docs"
    document_root.mkdir()
    config = AppConfig(
        index_path=tmp_path / "state" / "index.sqlite3",
        document_roots=(document_root,),
    )

    report = AppServices(config).run_doctor(
        required_imports=(("pathlib", "pathlib"), ("tomllib", "tomllib")),
    )

    assert report.ok
    assert "All checks passed." in format_doctor_report(report)


def test_cli_doctor_subcommand_runs(tmp_path) -> None:
    config_path = tmp_path / "office-agent.toml"
    document_root = tmp_path / "docs"
    document_root.mkdir()
    config_path.write_text(
        f"""
[offagent]
index_path = "{(tmp_path / 'state' / 'index.sqlite3').as_posix()}"
document_roots = ["{document_root.as_posix()}"]
""".strip()
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "offagent",
            "doctor",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Doctor Report" in result.stdout
    assert "[PASS] SQLite" in result.stdout
