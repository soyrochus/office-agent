from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from offagent.errors import InvalidArgumentsError

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - exercised through doctor checks
    load_dotenv = None

DEFAULT_CONFIG_PATH = Path("office-agent.toml")
DEFAULT_INDEX_PATH = Path(".offagent/index.sqlite3")
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDING_DIMENSIONS = 384
DEFAULT_VECTOR_SEARCH_TOP_K = 20
DEFAULT_HYBRID_KEYWORD_WEIGHT = 0.4
DEFAULT_HYBRID_SEMANTIC_WEIGHT = 0.6
ENV_CONFIG_PATH = "OFFAGENT_CONFIG"
ENV_INDEX_PATH = "OFFAGENT_INDEX_PATH"
ENV_DOCUMENT_ROOTS = "OFFAGENT_DOCUMENT_ROOTS"
ENV_ALLOWED_ROOTS = "OFFAGENT_ALLOWED_ROOTS"
ENV_OUTPUT_DIRECTORY = "OFFAGENT_OUTPUT_DIRECTORY"
ENV_OUTPUT_ROOTS = "OFFAGENT_OUTPUT_ROOTS"
ENV_ALLOW_INPLACE_OVERWRITE = "OFFAGENT_ALLOW_INPLACE_OVERWRITE"
ENV_EMBEDDING_MODEL = "OFFAGENT_EMBEDDING_MODEL"
ENV_EMBEDDING_DIMENSIONS = "OFFAGENT_EMBEDDING_DIMENSIONS"
ENV_VECTOR_SEARCH_TOP_K = "OFFAGENT_VECTOR_SEARCH_TOP_K"
ENV_HYBRID_KEYWORD_WEIGHT = "OFFAGENT_HYBRID_KEYWORD_WEIGHT"
ENV_HYBRID_SEMANTIC_WEIGHT = "OFFAGENT_HYBRID_SEMANTIC_WEIGHT"


@dataclass(frozen=True)
class AppConfig:
    index_path: Path = DEFAULT_INDEX_PATH
    document_roots: tuple[Path, ...] = ()
    allowed_roots: tuple[Path, ...] = ()
    output_directory: Path | None = None
    output_roots: tuple[Path, ...] = ()
    allow_inplace_overwrite: bool = True
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS
    vector_search_top_k: int = DEFAULT_VECTOR_SEARCH_TOP_K
    hybrid_keyword_weight: float = DEFAULT_HYBRID_KEYWORD_WEIGHT
    hybrid_semantic_weight: float = DEFAULT_HYBRID_SEMANTIC_WEIGHT
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
        "allowed_roots": (),
        "output_directory": None,
        "output_roots": (),
        "allow_inplace_overwrite": True,
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "embedding_dimensions": DEFAULT_EMBEDDING_DIMENSIONS,
        "vector_search_top_k": DEFAULT_VECTOR_SEARCH_TOP_K,
        "hybrid_keyword_weight": DEFAULT_HYBRID_KEYWORD_WEIGHT,
        "hybrid_semantic_weight": DEFAULT_HYBRID_SEMANTIC_WEIGHT,
        "config_path": selected_config_path,
    }

    if selected_config_path is not None:
        values.update(_load_file_values(selected_config_path))

    if ENV_INDEX_PATH in env_values:
        values["index_path"] = Path(env_values[ENV_INDEX_PATH]).expanduser()

    if ENV_DOCUMENT_ROOTS in env_values:
        values["document_roots"] = _split_paths(env_values[ENV_DOCUMENT_ROOTS])

    if ENV_ALLOWED_ROOTS in env_values:
        values["allowed_roots"] = _split_paths(env_values[ENV_ALLOWED_ROOTS])

    if ENV_OUTPUT_DIRECTORY in env_values:
        values["output_directory"] = Path(env_values[ENV_OUTPUT_DIRECTORY]).expanduser()

    if ENV_OUTPUT_ROOTS in env_values:
        values["output_roots"] = _split_paths(env_values[ENV_OUTPUT_ROOTS])

    if ENV_ALLOW_INPLACE_OVERWRITE in env_values:
        values["allow_inplace_overwrite"] = _parse_bool(env_values[ENV_ALLOW_INPLACE_OVERWRITE])

    if ENV_EMBEDDING_MODEL in env_values:
        values["embedding_model"] = env_values[ENV_EMBEDDING_MODEL]

    if ENV_EMBEDDING_DIMENSIONS in env_values:
        values["embedding_dimensions"] = _parse_int(
            env_values[ENV_EMBEDDING_DIMENSIONS],
            ENV_EMBEDDING_DIMENSIONS,
            minimum=1,
        )

    if ENV_VECTOR_SEARCH_TOP_K in env_values:
        values["vector_search_top_k"] = _parse_int(
            env_values[ENV_VECTOR_SEARCH_TOP_K],
            ENV_VECTOR_SEARCH_TOP_K,
            minimum=1,
        )

    if ENV_HYBRID_KEYWORD_WEIGHT in env_values:
        values["hybrid_keyword_weight"] = _parse_float(
            env_values[ENV_HYBRID_KEYWORD_WEIGHT],
            ENV_HYBRID_KEYWORD_WEIGHT,
            minimum=0.0,
        )

    if ENV_HYBRID_SEMANTIC_WEIGHT in env_values:
        values["hybrid_semantic_weight"] = _parse_float(
            env_values[ENV_HYBRID_SEMANTIC_WEIGHT],
            ENV_HYBRID_SEMANTIC_WEIGHT,
            minimum=0.0,
        )

    output_directory = _expand_optional_path(values["output_directory"])
    output_roots = tuple(Path(root).expanduser() for root in values["output_roots"])
    if not output_roots and output_directory is not None:
        output_roots = (output_directory,)

    return AppConfig(
        index_path=Path(values["index_path"]).expanduser(),
        document_roots=tuple(Path(root).expanduser() for root in values["document_roots"]),
        allowed_roots=tuple(Path(root).expanduser() for root in values["allowed_roots"]),
        output_directory=output_directory,
        output_roots=output_roots,
        allow_inplace_overwrite=bool(values["allow_inplace_overwrite"]),
        embedding_model=str(values["embedding_model"]),
        embedding_dimensions=int(values["embedding_dimensions"]),
        vector_search_top_k=int(values["vector_search_top_k"]),
        hybrid_keyword_weight=float(values["hybrid_keyword_weight"]),
        hybrid_semantic_weight=float(values["hybrid_semantic_weight"]),
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
    allowed_roots = payload.get("allowed_roots", ())
    output_roots = payload.get("output_roots", ())
    return {
        "index_path": Path(payload.get("index_path", DEFAULT_INDEX_PATH)).expanduser(),
        "document_roots": tuple(Path(root).expanduser() for root in roots),
        "allowed_roots": tuple(Path(root).expanduser() for root in allowed_roots),
        "output_directory": _optional_path(payload.get("output_directory")),
        "output_roots": tuple(Path(root).expanduser() for root in output_roots),
        "allow_inplace_overwrite": bool(payload.get("allow_inplace_overwrite", True)),
        "embedding_model": str(payload.get("embedding_model", DEFAULT_EMBEDDING_MODEL)),
        "embedding_dimensions": _coerce_int(
            payload.get("embedding_dimensions", DEFAULT_EMBEDDING_DIMENSIONS),
            "embedding_dimensions",
            minimum=1,
        ),
        "vector_search_top_k": _coerce_int(
            payload.get("vector_search_top_k", DEFAULT_VECTOR_SEARCH_TOP_K),
            "vector_search_top_k",
            minimum=1,
        ),
        "hybrid_keyword_weight": _coerce_float(
            payload.get("hybrid_keyword_weight", DEFAULT_HYBRID_KEYWORD_WEIGHT),
            "hybrid_keyword_weight",
            minimum=0.0,
        ),
        "hybrid_semantic_weight": _coerce_float(
            payload.get("hybrid_semantic_weight", DEFAULT_HYBRID_SEMANTIC_WEIGHT),
            "hybrid_semantic_weight",
            minimum=0.0,
        ),
    }


def _split_paths(value: str) -> tuple[Path, ...]:
    if not value.strip():
        return ()
    return tuple(Path(part).expanduser() for part in value.split(os.pathsep) if part)


def _optional_path(value: object) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value)).expanduser()


def _expand_optional_path(value: object) -> Path | None:
    if value is None:
        return None
    return Path(value).expanduser()


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise InvalidArgumentsError(f"Invalid boolean value: {value}")


def _parse_int(value: str, name: str, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise InvalidArgumentsError(f"Invalid integer value for {name}: {value}") from exc
    if minimum is not None and parsed < minimum:
        raise InvalidArgumentsError(f"{name} must be >= {minimum}")
    return parsed


def _parse_float(value: str, name: str, *, minimum: float | None = None) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise InvalidArgumentsError(f"Invalid float value for {name}: {value}") from exc
    if minimum is not None and parsed < minimum:
        raise InvalidArgumentsError(f"{name} must be >= {minimum}")
    return parsed


def _coerce_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool):
        raise InvalidArgumentsError(f"Invalid integer value for {name}: {value}")
    if isinstance(value, int):
        parsed = value
    else:
        parsed = _parse_int(str(value), name, minimum=minimum)
    if minimum is not None and parsed < minimum:
        raise InvalidArgumentsError(f"{name} must be >= {minimum}")
    return parsed


def _coerce_float(value: object, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool):
        raise InvalidArgumentsError(f"Invalid float value for {name}: {value}")
    if isinstance(value, (int, float)):
        parsed = float(value)
    else:
        parsed = _parse_float(str(value), name, minimum=minimum)
    if minimum is not None and parsed < minimum:
        raise InvalidArgumentsError(f"{name} must be >= {minimum}")
    return parsed
