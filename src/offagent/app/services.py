from __future__ import annotations

import hashlib
import importlib
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from offagent.adapters import docx_adapter, pptx_adapter
from offagent.config import AppConfig
from offagent.domain.models import DocumentRef, FileType, ItemRef, SearchHit
from offagent.indexing import store

SUPPORTED_EXTENSIONS: dict[str, FileType] = {
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
}
INDEXABLE_EXTENSIONS: dict[str, FileType] = {
    ".docx": "docx",
    ".pptx": "pptx",
}

REQUIRED_IMPORTS: tuple[tuple[str, str], ...] = (
    ("typer", "Typer"),
    ("pydantic", "Pydantic"),
    ("dotenv", "python-dotenv"),
    ("docx", "python-docx"),
    ("pptx", "python-pptx"),
)


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


@dataclass(frozen=True)
class IndexSummary:
    files_scanned: int
    files_indexed: int
    files_skipped: int


@dataclass(frozen=True)
class PatchResult:
    document_path: Path
    output_path: Path
    item: ItemRef
    text: str


@dataclass
class AppServices:
    config: AppConfig

    def discover_documents(self) -> list[DocumentRef]:
        return discover_documents(self.config.document_roots)

    def index_path(self, path: Path) -> IndexSummary:
        candidates = _index_candidates(path)
        indexed = 0
        skipped = 0

        for candidate in candidates:
            if candidate.suffix.lower() not in INDEXABLE_EXTENSIONS:
                skipped += 1
                continue
            self.index_document(candidate)
            indexed += 1

        return IndexSummary(
            files_scanned=len(candidates),
            files_indexed=indexed,
            files_skipped=skipped,
        )

    def reindex_path(self, path: Path) -> IndexSummary:
        return self.index_path(path)

    def index_document(self, document_path: Path) -> DocumentRef:
        resolved_path, file_type = _require_indexable_path(document_path)
        document_ref = _build_document_ref(resolved_path, file_type)
        items = _extract_items(resolved_path, file_type)

        connection = store.ensure_ready(self.config.index_path)
        try:
            store.upsert_document(connection, document_ref)
            store.replace_document_items(connection, document_ref.document_id, items)
        finally:
            connection.close()

        return document_ref

    def search_corpus(
        self,
        query: str,
        *,
        file_type: str | None = None,
        document_path: Path | None = None,
    ) -> list[SearchHit]:
        if file_type not in (None, "docx", "pptx"):
            raise ValueError("Only DOCX and PPTX search are supported in this feature.")

        connection = store.ensure_ready(self.config.index_path)
        try:
            rows = store.search_items(
                connection,
                query,
                file_type=file_type,
                document_path=document_path,
            )
        finally:
            connection.close()

        return [_search_hit_from_row(row) for row in rows]

    def locate_paragraph(self, document_path: Path, paragraph_index: int) -> ItemRef:
        return self.locate_items(document_path, paragraph_index=paragraph_index)[0]

    def locate_slide_shapes(
        self,
        document_path: Path,
        slide_number: int,
        shape_id: int | None = None,
    ) -> list[ItemRef]:
        return self.locate_items(document_path, slide_number=slide_number, shape_id=shape_id)

    def locate_items(
        self,
        document_path: Path,
        *,
        paragraph_index: int | None = None,
        slide_number: int | None = None,
        shape_id: int | None = None,
    ) -> list[ItemRef]:
        resolved_path, file_type = _require_indexable_path(document_path)
        connection = store.ensure_ready(self.config.index_path)
        try:
            document_row = self._resolve_document_row(connection, resolved_path)
            if file_type == "docx":
                if paragraph_index is None or slide_number is not None or shape_id is not None:
                    raise ValueError("DOCX locate requires --paragraph and does not support --slide.")
                item_row = self._resolve_indexed_item_row(
                    connection,
                    document_row,
                    f"para:{paragraph_index}",
                    resolved_path,
                )
                return [_item_ref_from_row(item_row)]

            if paragraph_index is not None:
                raise ValueError("PPTX locate does not support --paragraph.")
            if slide_number is None:
                raise ValueError("PPTX locate requires --slide.")

            item_rows = store.fetch_items_for_document(connection, document_row["document_id"])
            matches = [
                row
                for row in item_rows
                if _metadata_value(row, "slide_number") == slide_number
                and (shape_id is None or _metadata_value(row, "shape_id") == shape_id)
            ]
            matches.sort(
                key=lambda row: (
                    _metadata_value(row, "shape_index", default=0),
                    row["item_id"],
                )
            )
            if not matches:
                if shape_id is None:
                    raise LookupError(
                        f"No indexed PPTX text shapes found on slide {slide_number} for {resolved_path}"
                    )
                raise LookupError(
                    f"No indexed PPTX text shape found for slide {slide_number} shape {shape_id} in {resolved_path}"
                )
            return [_item_ref_from_row(row) for row in matches]
        finally:
            connection.close()

    def read_item(self, document_path: Path, item_id: str) -> str:
        resolved_path, file_type = _require_indexable_path(document_path)
        connection = store.ensure_ready(self.config.index_path)
        try:
            document_row = self._resolve_document_row(connection, resolved_path)
            self._resolve_indexed_item_row(connection, document_row, item_id, resolved_path)
        finally:
            connection.close()
        if file_type == "docx":
            return docx_adapter.read_paragraph(resolved_path, item_id)
        return pptx_adapter.read_text_shape(resolved_path, item_id)

    def replace_item_text(self, document_path: Path, item_id: str, text: str) -> PatchResult:
        resolved_path, file_type = _require_indexable_path(document_path)
        connection = store.ensure_ready(self.config.index_path)
        try:
            document_row = self._resolve_document_row(connection, resolved_path)
            try:
                self._resolve_indexed_item_row(connection, document_row, item_id, resolved_path)
            except LookupError:
                if file_type == "pptx":
                    _raise_if_pptx_target_not_editable(resolved_path, item_id)
                raise
        finally:
            connection.close()

        if file_type == "docx":
            output_path = docx_adapter.replace_paragraph(resolved_path, item_id, text)
            updated_text = docx_adapter.read_paragraph(output_path, item_id)
        else:
            output_path = pptx_adapter.replace_text_shape(resolved_path, item_id, text)
            updated_text = pptx_adapter.read_text_shape(output_path, item_id)
        self.index_document(output_path)

        connection = store.ensure_ready(self.config.index_path)
        try:
            document_row = self._resolve_document_row(connection, output_path.resolve())
            updated_item_row = self._resolve_indexed_item_row(
                connection,
                document_row,
                item_id,
                output_path.resolve(),
            )
        finally:
            connection.close()

        return PatchResult(
            document_path=resolved_path,
            output_path=output_path,
            item=_item_ref_from_row(updated_item_row),
            text=updated_text,
        )

    def append_item_text(self, document_path: Path, item_id: str, text: str) -> PatchResult:
        resolved_path, file_type = _require_indexable_path(document_path)
        connection = store.ensure_ready(self.config.index_path)
        try:
            document_row = self._resolve_document_row(connection, resolved_path)
            try:
                self._resolve_indexed_item_row(connection, document_row, item_id, resolved_path)
            except LookupError:
                if file_type == "pptx":
                    _raise_if_pptx_target_not_editable(resolved_path, item_id)
                raise
        finally:
            connection.close()

        if file_type == "docx":
            output_path = docx_adapter.append_paragraph(resolved_path, item_id, text)
            updated_text = docx_adapter.read_paragraph(output_path, item_id)
        else:
            output_path = pptx_adapter.append_text_shape(resolved_path, item_id, text)
            updated_text = pptx_adapter.read_text_shape(output_path, item_id)
        self.index_document(output_path)

        connection = store.ensure_ready(self.config.index_path)
        try:
            document_row = self._resolve_document_row(connection, output_path.resolve())
            updated_item_row = self._resolve_indexed_item_row(
                connection,
                document_row,
                item_id,
                output_path.resolve(),
            )
        finally:
            connection.close()

        return PatchResult(
            document_path=resolved_path,
            output_path=output_path,
            item=_item_ref_from_row(updated_item_row),
            text=updated_text,
        )

    def run_doctor(
        self,
        required_imports: Sequence[tuple[str, str]] | None = None,
    ) -> DoctorReport:
        checks: list[DoctorCheck] = []

        for module_name, label in required_imports or REQUIRED_IMPORTS:
            checks.append(_check_import(module_name, label))

        checks.append(_check_sqlite_module())
        checks.append(_check_fts5_support())
        checks.append(_check_index_path(self.config.index_path))
        checks.extend(_check_document_roots(self.config.document_roots))

        return DoctorReport(checks=tuple(checks))

    def _resolve_item_row(
        self,
        connection: sqlite3.Connection,
        document_path: Path,
        item_id: str,
    ) -> tuple[sqlite3.Row, sqlite3.Row]:
        resolved_path, _ = _require_indexable_path(document_path)
        document_row = self._resolve_document_row(connection, resolved_path)
        item_row = self._resolve_indexed_item_row(connection, document_row, item_id, resolved_path)
        return document_row, item_row

    def _resolve_document_row(
        self,
        connection: sqlite3.Connection,
        document_path: Path,
    ) -> sqlite3.Row:
        document_row = store.fetch_document_by_path(connection, document_path)
        if document_row is None:
            raise LookupError(f"Document is not indexed: {document_path}")
        return document_row

    def _resolve_indexed_item_row(
        self,
        connection: sqlite3.Connection,
        document_row: sqlite3.Row,
        item_id: str,
        document_path: Path,
    ) -> sqlite3.Row:
        item_row = store.fetch_item_by_id(connection, document_row["document_id"], item_id)
        if item_row is None:
            raise LookupError(f"Item {item_id} is not indexed for {document_path}")
        return item_row


def discover_documents(roots: Iterable[Path]) -> list[DocumentRef]:
    documents: list[DocumentRef] = []

    for root in roots:
        if not root.exists() or not root.is_dir():
            continue

        for candidate in sorted(root.rglob("*"), key=lambda path: str(path)):
            if not candidate.is_file():
                continue

            extension = candidate.suffix.lower()
            if extension not in SUPPORTED_EXTENSIONS:
                continue

            documents.append(_build_document_ref(candidate, SUPPORTED_EXTENSIONS[extension]))

    return documents


def format_doctor_report(report: DoctorReport) -> str:
    lines = ["Doctor Report"]
    for check in report.checks:
        status = "PASS" if check.ok else "FAIL"
        lines.append(f"[{status}] {check.name}: {check.detail}")

    summary = "All checks passed." if report.ok else "One or more checks failed."
    lines.append(summary)
    return "\n".join(lines)


def _build_document_ref(path: Path, file_type: FileType) -> DocumentRef:
    resolved = path.resolve()
    document_id = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()
    stat_result = resolved.stat()
    content_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return DocumentRef(
        document_id=document_id,
        path=resolved,
        file_type=file_type,
        display_name=resolved.name,
        modified_time=stat_result.st_mtime,
        content_hash=content_hash,
    )


def _index_candidates(path: Path) -> list[Path]:
    resolved = path.resolve()
    if resolved.is_dir():
        return sorted(
            [
                candidate
                for candidate in resolved.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS
            ],
            key=lambda candidate: str(candidate),
        )
    return [resolved]


def _require_indexable_path(path: Path) -> tuple[Path, FileType]:
    resolved = path.resolve()
    file_type = INDEXABLE_EXTENSIONS.get(resolved.suffix.lower())
    if file_type is None:
        raise ValueError(f"Implemented operations require a .docx or .pptx path: {path}")
    if not resolved.exists():
        raise FileNotFoundError(resolved)
    return resolved, file_type


def _extract_items(document_path: Path, file_type: FileType):
    if file_type == "docx":
        return docx_adapter.extract_document(document_path)
    if file_type == "pptx":
        return pptx_adapter.extract_document(document_path)
    raise ValueError(f"Unsupported indexable file type: {file_type}")


def _search_hit_from_row(row: sqlite3.Row) -> SearchHit:
    return SearchHit(
        document_id=row["document_id"],
        item_id=row["item_id"],
        score=float(row["score"]),
        matched_text=row["content_text"],
        locator=row["locator"],
        item_type=row["item_type"],
        preview=row["preview"],
        document_path=Path(row["path"]),
        display_name=row["display_name"],
    )


def _item_ref_from_row(row: sqlite3.Row) -> ItemRef:
    return ItemRef(
        document_id=row["document_id"],
        item_id=row["item_id"],
        item_type=row["item_type"],
        locator=row["locator"],
        preview=row["preview"],
        metadata=json.loads(row["metadata_json"]),
    )


def _metadata_value(row: sqlite3.Row, key: str, *, default=None):
    metadata = json.loads(row["metadata_json"])
    return metadata.get(key, default)


def _raise_if_pptx_target_not_editable(document_path: Path, item_id: str) -> None:
    try:
        pptx_adapter.resolve_shape(document_path, item_id)
    except pptx_adapter.TargetNotEditableError:
        raise
    except (LookupError, ValueError):
        return


def _check_import(module_name: str, label: str) -> DoctorCheck:
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        return DoctorCheck(label, False, f"Import failed: {exc}")
    return DoctorCheck(label, True, "Import succeeded.")


def _check_sqlite_module() -> DoctorCheck:
    try:
        sqlite3.connect(":memory:").close()
    except sqlite3.Error as exc:
        return DoctorCheck("SQLite", False, f"Connection failed: {exc}")
    return DoctorCheck("SQLite", True, "Connection succeeded.")


def _check_fts5_support() -> DoctorCheck:
    connection = sqlite3.connect(":memory:")
    try:
        if store.supports_fts5(connection):
            return DoctorCheck("SQLite FTS5", True, "FTS5 virtual tables are available.")
        return DoctorCheck("SQLite FTS5", False, "FTS5 virtual tables are unavailable.")
    finally:
        connection.close()


def _check_index_path(index_path: Path) -> DoctorCheck:
    try:
        connection = store.ensure_ready(index_path)
    except (OSError, sqlite3.Error, store.StoreCapabilityError) as exc:
        return DoctorCheck("Index Path", False, f"Schema bootstrap failed: {exc}")
    else:
        connection.close()
        return DoctorCheck("Index Path", True, f"Schema ready at {index_path}.")


def _check_document_roots(roots: Sequence[Path]) -> list[DoctorCheck]:
    if not roots:
        return [DoctorCheck("Document Roots", True, "No document roots configured.")]

    checks: list[DoctorCheck] = []
    for root in roots:
        if root.exists() and root.is_dir() and os.access(root, os.R_OK):
            checks.append(DoctorCheck(f"Document Root {root}", True, "Readable directory."))
        elif not root.exists():
            checks.append(DoctorCheck(f"Document Root {root}", False, "Path does not exist."))
        elif not root.is_dir():
            checks.append(DoctorCheck(f"Document Root {root}", False, "Path is not a directory."))
        else:
            checks.append(DoctorCheck(f"Document Root {root}", False, "Directory is not readable."))
    return checks
