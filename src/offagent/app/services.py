from __future__ import annotations

import hashlib
import importlib
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from offagent.config import AppConfig
from offagent.domain.models import DocumentRef, FileType
from offagent.indexing import store

SUPPORTED_EXTENSIONS: dict[str, FileType] = {
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
}

REQUIRED_IMPORTS: tuple[tuple[str, str], ...] = (
    ("typer", "Typer"),
    ("pydantic", "Pydantic"),
    ("dotenv", "python-dotenv"),
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


@dataclass
class AppServices:
    config: AppConfig

    def discover_documents(self) -> list[DocumentRef]:
        return discover_documents(self.config.document_roots)

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
    return DocumentRef(
        document_id=document_id,
        path=resolved,
        file_type=file_type,
        display_name=resolved.name,
        modified_time=stat_result.st_mtime,
        content_hash=None,
    )


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
