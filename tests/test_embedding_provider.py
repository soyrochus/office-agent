from __future__ import annotations

import struct

from offagent.adapters.embedding_provider import LocalEmbeddingProvider


def test_local_embedding_provider_returns_stable_blob_vectors() -> None:
    provider = LocalEmbeddingProvider(model_name="hash://unit-test", dimensions=24)

    first = provider.embed_texts(["Supplier shall review variance."])[0]
    second = provider.embed_texts(["Supplier shall review variance."])[0]

    assert provider.dimensions == 24
    assert len(first) == 24 * 4
    assert first == second
    assert any(value != 0.0 for value in struct.unpack("<24f", first))
