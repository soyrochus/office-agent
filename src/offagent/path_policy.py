from __future__ import annotations

from pathlib import Path
from typing import Sequence

from offagent.errors import PolicyRefusedError, TargetNotFoundError


def canonicalize_existing_path(path: Path) -> Path:
    candidate = Path(path).expanduser()
    try:
        return candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise TargetNotFoundError(f"Path does not exist: {candidate}") from exc


def canonicalize_output_path(path: Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def normalize_roots(roots: Sequence[Path]) -> tuple[Path, ...]:
    return tuple(Path(root).expanduser().resolve(strict=False) for root in roots)


def ensure_path_allowed(
    path: Path,
    roots: Sequence[Path],
    *,
    label: str,
    policy_name: str,
) -> Path:
    resolved = Path(path).expanduser().resolve(strict=False)
    normalized_roots = normalize_roots(roots)
    if not normalized_roots:
        return resolved
    if any(_is_relative_to(resolved, root) for root in normalized_roots):
        return resolved
    raise PolicyRefusedError(f"{label} is outside configured {policy_name}: {resolved}")


def _is_relative_to(path: Path, root: Path) -> bool:
    return path == root or root in path.parents
