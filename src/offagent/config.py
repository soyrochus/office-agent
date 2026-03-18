from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - exercised through doctor checks
    load_dotenv = None

DEFAULT_CONFIG_PATH = Path("office-agent.toml")
DEFAULT_INDEX_PATH = Path(".offagent/index.sqlite3")
ENV_CONFIG_PATH = "OFFAGENT_CONFIG"
ENV_INDEX_PATH = "OFFAGENT_INDEX_PATH"
ENV_DOCUMENT_ROOTS = "OFFAGENT_DOCUMENT_ROOTS"


@dataclass(frozen=True)
class AppConfig:
    index_path: Path = DEFAULT_INDEX_PATH
    document_roots: tuple[Path, ...] = ()
    config_path: Path | None = None


def load_config(
    config_path: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> AppConfig:
    if load_dotenv is not None:
        load_dotenv()

    env_values = dict(os.environ if env is None else env)
    selected_config_path = _select_config_path(config_path, env_values)

    values: dict[str, object] = {
        "index_path": DEFAULT_INDEX_PATH,
        "document_roots": (),
        "config_path": selected_config_path,
    }

    if selected_config_path is not None:
        values.update(_load_file_values(selected_config_path))

    if ENV_INDEX_PATH in env_values:
        values["index_path"] = Path(env_values[ENV_INDEX_PATH]).expanduser()

    if ENV_DOCUMENT_ROOTS in env_values:
        values["document_roots"] = _split_document_roots(env_values[ENV_DOCUMENT_ROOTS])

    return AppConfig(
        index_path=Path(values["index_path"]).expanduser(),
        document_roots=tuple(Path(root).expanduser() for root in values["document_roots"]),
        config_path=selected_config_path,
    )


def _select_config_path(config_path: Path | None, env: Mapping[str, str]) -> Path | None:
    if config_path is not None:
        selected = config_path.expanduser()
        if not selected.exists():
            raise FileNotFoundError(selected)
        return selected

    if ENV_CONFIG_PATH in env:
        selected = Path(env[ENV_CONFIG_PATH]).expanduser()
        if not selected.exists():
            raise FileNotFoundError(selected)
        return selected

    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH

    return None


def _load_file_values(config_path: Path) -> dict[str, object]:
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    payload = raw.get("offagent", raw)
    roots = payload.get("document_roots", ())
    return {
        "index_path": Path(payload.get("index_path", DEFAULT_INDEX_PATH)).expanduser(),
        "document_roots": tuple(Path(root).expanduser() for root in roots),
    }


def _split_document_roots(value: str) -> tuple[Path, ...]:
    if not value.strip():
        return ()
    return tuple(Path(part).expanduser() for part in value.split(os.pathsep) if part)
