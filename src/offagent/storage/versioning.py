from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def build_versioned_output_path(
    source_path: Path,
    *,
    output_directory: Path | None = None,
    timestamp: datetime | None = None,
    create_directory: bool = True,
) -> Path:
    source = source_path.resolve()
    target_directory = source.parent if output_directory is None else output_directory.expanduser()
    if create_directory:
        target_directory.mkdir(parents=True, exist_ok=True)
    rendered_timestamp = _render_timestamp(timestamp)
    filename = f"{source.stem}.edited.{rendered_timestamp}{source.suffix}"
    return target_directory / filename


def _render_timestamp(timestamp: datetime | None) -> str:
    current = datetime.now(timezone.utc) if timestamp is None else timestamp.astimezone(timezone.utc)
    return current.strftime("%Y%m%d-%H%M%S%f")
