from __future__ import annotations

import hashlib
import math
import re
import struct
from collections.abc import Callable
from typing import Protocol

try:
    from fastembed import TextEmbedding as FastEmbedTextEmbedding
except ModuleNotFoundError:  # pragma: no cover - exercised by tests that simulate missing dependency
    FastEmbedTextEmbedding = None

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed_texts(
        self,
        texts: list[str],
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[bytes]:
        """Return one float32 blob per input text."""


class LocalEmbeddingProvider:
    """Local embedding provider that prefers fastembed and falls back to hashing vectors."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        *,
        dimensions: int | None = None,
    ) -> None:
        self.model_name = model_name
        self._backend = _build_backend(model_name, dimensions)
        self.dimensions = self._backend.dimensions

    def embed_texts(
        self,
        texts: list[str],
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[bytes]:
        return [
            struct.pack(f"<{self.dimensions}f", *vector)
            for vector in self._backend.embed(texts, on_progress=on_progress)
        ]


class _FastEmbedBackend:
    def __init__(self, model_name: str) -> None:
        if FastEmbedTextEmbedding is None:
            raise RuntimeError("fastembed is not installed.")
        self._model = FastEmbedTextEmbedding(model_name=model_name)
        probe = next(self._model.embed(["probe"]))
        self.dimensions = len(probe)

    def embed(
        self,
        texts: list[str],
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[list[float]]:
        results: list[list[float]] = []
        total = len(texts)
        for index, vector in enumerate(self._model.embed(texts), start=1):
            results.append(list(map(float, vector)))
            if on_progress is not None:
                on_progress(index, total)
        return results


class _HashingBackend:
    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def embed(
        self,
        texts: list[str],
        *,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[list[float]]:
        results: list[list[float]] = []
        total = len(texts)
        for index, text in enumerate(texts, start=1):
            results.append(_hash_text_to_unit_vector(text, self.dimensions))
            if on_progress is not None:
                on_progress(index, total)
        return results


def _build_backend(model_name: str, dimensions: int | None):
    if model_name.startswith("hash://"):
        return _HashingBackend(dimensions or 384)
    if FastEmbedTextEmbedding is not None:
        backend = _FastEmbedBackend(model_name)
        if dimensions is not None and backend.dimensions != dimensions:
            raise RuntimeError(
                f"Configured embedding dimensions {dimensions} do not match model dimensions {backend.dimensions}."
            )
        return backend

    return _HashingBackend(dimensions or 384)


def _hash_text_to_unit_vector(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    tokens = TOKEN_PATTERN.findall(text.lower())
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for offset in range(0, 8, 4):
            bucket = int.from_bytes(digest[offset : offset + 2], "little") % dimensions
            sign = 1.0 if digest[offset + 2] % 2 == 0 else -1.0
            weight = 1.0 + (digest[offset + 3] / 255.0)
            vector[bucket] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]
