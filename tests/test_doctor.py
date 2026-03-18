from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import subprocess
import sys

from offagent.app.services import AppServices, format_doctor_report
from offagent.config import AppConfig


class DoctorTests(unittest.TestCase):
    def test_doctor_reports_pass_for_bootstrap_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            document_root = temp_path / "docs"
            document_root.mkdir()
            config = AppConfig(
                index_path=temp_path / "state" / "index.sqlite3",
                document_roots=(document_root,),
            )

            report = AppServices(config).run_doctor(
                required_imports=(("pathlib", "pathlib"), ("tomllib", "tomllib")),
            )

            self.assertTrue(report.ok)
            self.assertIn("All checks passed.", format_doctor_report(report))

    def test_cli_doctor_subcommand_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "office-agent.toml"
            document_root = temp_path / "docs"
            document_root.mkdir()
            config_path.write_text(
                f"""
[offagent]
index_path = "{(temp_path / 'state' / 'index.sqlite3').as_posix()}"
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

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Doctor Report", result.stdout)
            self.assertIn("[PASS] SQLite", result.stdout)


if __name__ == "__main__":
    unittest.main()
