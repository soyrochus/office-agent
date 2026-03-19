from __future__ import annotations

import shutil

import pytest

from offagent.app.services import AppServices
from offagent.config import AppConfig
from offagent.errors import PolicyRefusedError


def test_path_guards_use_canonical_paths_for_allowed_reads(sample_docx, tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    document_path = docs_dir / "sample.docx"
    shutil.copy2(sample_docx, document_path)

    services = AppServices(
        AppConfig(
            index_path=tmp_path / "state" / "index.sqlite3",
            document_roots=(docs_dir,),
            allowed_roots=(docs_dir,),
        )
    )

    traversal_path = docs_dir / ".." / "docs" / "sample.docx"
    summary = services.index_path(traversal_path)

    assert summary.files_indexed == 1


def test_path_guards_refuse_symlinked_reads_outside_allowed_roots(sample_docx, tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    secret_path = secret_dir / "secret.docx"
    shutil.copy2(sample_docx, secret_path)
    symlink_path = docs_dir / "linked-secret.docx"
    symlink_path.symlink_to(secret_path)

    services = AppServices(
        AppConfig(
            index_path=tmp_path / "state" / "index.sqlite3",
            document_roots=(docs_dir,),
            allowed_roots=(docs_dir,),
        )
    )

    with pytest.raises(PolicyRefusedError, match="allowed roots"):
        services.index_path(symlink_path)


def test_path_guards_refuse_versioned_writes_outside_output_roots(sample_docx, tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    document_path = docs_dir / "sample.docx"
    shutil.copy2(sample_docx, document_path)
    services = AppServices(
        AppConfig(
            index_path=tmp_path / "state" / "index.sqlite3",
            document_roots=(docs_dir,),
            allowed_roots=(docs_dir,),
            output_directory=tmp_path / "edited-outside",
            output_roots=(tmp_path / "approved-outputs",),
        )
    )
    services.index_document(document_path)

    with pytest.raises(PolicyRefusedError, match="output roots"):
        services.replace_item_text(document_path, "para:1", "Blocked output.")
