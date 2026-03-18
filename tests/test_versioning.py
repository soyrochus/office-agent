from __future__ import annotations

from datetime import datetime, timezone

from offagent.storage.versioning import build_versioned_output_path


def test_build_versioned_output_path_uses_directory_and_timestamp(tmp_path) -> None:
    source_path = tmp_path / "sample.report.docx"
    source_path.write_text("placeholder")

    output_path = build_versioned_output_path(
        source_path,
        output_directory=tmp_path / "edited",
        timestamp=datetime(2026, 3, 18, 21, 45, 12, 345678, tzinfo=timezone.utc),
    )

    assert output_path == tmp_path / "edited" / "sample.report.edited.20260318-214512345678.docx"
    assert output_path.parent.exists()
