from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from offagent.app.services import DoctorReport, IndexSummary, PatchResult
from offagent.domain.models import DocumentRef, ItemRef, SearchHit


def emit_output(
    payload: Any,
    *,
    as_json: bool,
    quiet: bool,
    human_renderer: Callable[[Any], str],
    echo: Callable[[str], None],
) -> None:
    if quiet:
        return
    if as_json:
        echo(json.dumps(to_jsonable(payload), indent=2, sort_keys=True))
        return
    echo(human_renderer(payload))


def to_jsonable(value: Any) -> Any:
    if isinstance(value, DoctorReport):
        return {"ok": value.ok, "checks": to_jsonable(value.checks)}
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def render_doctor_report(report: DoctorReport) -> str:
    lines = ["Doctor Report"]
    for check in report.checks:
        status = "PASS" if check.ok else "FAIL"
        lines.append(f"[{status}] {check.name}: {check.detail}")
    lines.append("All checks passed." if report.ok else "One or more checks failed.")
    return "\n".join(lines)


def render_index_summary(payload: dict[str, Any]) -> str:
    path = payload["path"]
    summary: IndexSummary = payload["summary"]
    return (
        f"path={path}\tfiles_scanned={summary.files_scanned}\tfiles_indexed={summary.files_indexed}"
        f"\tfiles_skipped={summary.files_skipped}"
    )


def render_search_hits(hits: Sequence[SearchHit]) -> str:
    if not hits:
        return "No matches found."
    lines: list[str] = []
    for hit in hits:
        lines.append(
            f"{hit.item_id}\tscore={hit.score:.3f}\tdoc={hit.display_name or hit.document_path}"
        )
        lines.append(hit.preview)
    return "\n".join(lines)


def render_items(items: Sequence[ItemRef]) -> str:
    if not items:
        return "No items found."
    return "\n".join(f"{item.item_id}\t{item.locator}\t{item.preview}" for item in items)


def render_patch_result(result: PatchResult) -> str:
    return f"{result.item.item_id}\tupdated\t{result.output_path}"


def render_documents(documents: Sequence[DocumentRef]) -> str:
    if not documents:
        return "No indexed documents."
    return "\n".join(
        (
            f"{document.document_id}\ttype={document.file_type}\titems={document.item_count or 0}"
            f"\tpath={document.path}"
        )
        for document in documents
    )


def render_document(document: DocumentRef) -> str:
    lines = [
        f"document_id: {document.document_id}",
        f"path: {document.path}",
        f"file_type: {document.file_type}",
        f"display_name: {document.display_name}",
        f"modified_time: {document.modified_time}",
        f"item_count: {document.item_count or 0}",
    ]
    if document.content_hash is not None:
        lines.append(f"content_hash: {document.content_hash}")
    return "\n".join(lines)


def render_item(item: ItemRef) -> str:
    lines = [
        f"document_id: {item.document_id}",
        f"item_id: {item.item_id}",
        f"item_type: {item.item_type}",
        f"locator: {item.locator}",
        f"preview: {item.preview}",
    ]
    if item.content_text is not None:
        lines.append(f"content_text: {item.content_text}")
    if item.metadata:
        lines.append("metadata:")
        for key, value in sorted(item.metadata.items()):
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def render_text_result(payload: dict[str, Any]) -> str:
    return str(payload["text"])
