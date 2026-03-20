from __future__ import annotations

import sqlite3

import pytest

from offagent.app.services import AppServices
from offagent.config import AppConfig
from offagent.errors import NoEmbeddingsError


def _vector_config(tmp_path) -> AppConfig:
    return AppConfig(
        index_path=tmp_path / "state" / "index.sqlite3",
        document_roots=(tmp_path,),
        embedding_model="hash://services",
        embedding_dimensions=48,
        vector_search_top_k=10,
    )


def test_index_document_with_embeddings_persists_embedding_rows(sample_docx, tmp_path) -> None:
    services = AppServices(_vector_config(tmp_path))

    services.index_document(sample_docx, with_embeddings=True)

    connection = sqlite3.connect(tmp_path / "state" / "index.sqlite3")
    try:
        row_count = connection.execute("SELECT COUNT(*) FROM item_embeddings").fetchone()[0]
        dimensions = connection.execute(
            "SELECT DISTINCT dimensions FROM item_embeddings"
        ).fetchone()[0]
    finally:
        connection.close()

    assert row_count == 4
    assert dimensions == 48


def test_semantic_and_hybrid_search_return_mode_metadata(sample_docx, tmp_path) -> None:
    services = AppServices(_vector_config(tmp_path))
    services.index_document(sample_docx, with_embeddings=True)

    semantic_hits = services.search_corpus("supplier shall", file_type="docx", mode="semantic")
    hybrid_hits = services.search_corpus("supplier shall", file_type="docx", mode="hybrid")

    assert semantic_hits[0].item_id == "para:3"
    assert semantic_hits[0].match_mode == "semantic"
    assert semantic_hits[0].scores is not None
    assert "semantic" in semantic_hits[0].scores
    assert hybrid_hits[0].item_id == "para:3"
    assert hybrid_hits[0].match_mode == "hybrid"
    assert hybrid_hits[0].scores is not None
    assert {"keyword", "semantic", "final"} <= set(hybrid_hits[0].scores)


def test_semantic_search_requires_indexed_embeddings(sample_docx, tmp_path) -> None:
    services = AppServices(_vector_config(tmp_path))
    services.index_document(sample_docx)

    with pytest.raises(NoEmbeddingsError, match="Reindex with --with-embeddings"):
        services.search_corpus("supplier shall", file_type="docx", mode="semantic")
