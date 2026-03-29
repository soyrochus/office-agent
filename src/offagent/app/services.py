from __future__ import annotations

import hashlib
import importlib
import json
import logging
import os
from copy import deepcopy
import sqlite3
import struct
import shutil
import tempfile
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Sequence

from offagent.adapters import docx_adapter, embedding_provider, pptx_adapter, xlsx_adapter
from offagent.app.progress import NullProgressReporter, ProgressReporter
from offagent.config import AppConfig
from offagent.domain.locators import parse_locator, to_legacy_locator, to_v2_locator
from offagent.domain.models import (
    BatchResult,
    BlockBundle,
    ChildSummary,
    Capability,
    DocxTableEntry,
    DocxTablesResult,
    DocumentBlock,
    DocumentBlocks,
    DocumentRef,
    DocumentStructure,
    FileType,
    IndexedItem,
    InsertContentResult,
    ItemRef,
    NodePayload,
    NodeWriteResult,
    ObjectPayload,
    MutationResult,
    ParagraphCollection,
    PresentationStructure,
    SearchHit,
    SearchMode,
    SectionPayload,
    SheetSnapshot,
    SlideNotes,
    StructureUnit,
    StructureCollection,
    StructuredTarget,
    StructuredWriteResult,
    TableCollection,
    WorkbookStructure,
    WorksheetSummary,
    XlsxInsertRowsResult,
    XlsxRowEmbedding,
)
from offagent.errors import (
    InvalidArgumentsError,
    NoEmbeddingsError,
    PolicyRefusedError,
    StaleLocatorError,
    TargetNotEditableError,
)
from offagent.errors import TargetNotFoundError
from offagent.indexing import store
from offagent.objects import docx_objects, pptx_objects, xlsx_objects
from offagent.objects.docx_objects import DocxObjectResolver
from offagent.objects.pptx_objects import PptxObjectResolver
from offagent.objects.xlsx_objects import XlsxObjectResolver
from offagent.path_policy import (
    canonicalize_existing_path,
    canonicalize_output_path,
    ensure_path_allowed,
    normalize_roots,
)
from offagent.storage import versioning

LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: dict[str, FileType] = {
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
}
INDEXABLE_EXTENSIONS: dict[str, FileType] = {
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
}

REQUIRED_IMPORTS: tuple[tuple[str, str], ...] = (
    ("mcp", "MCP Python SDK"),
    ("typer", "Typer"),
    ("pydantic", "Pydantic"),
    ("dotenv", "python-dotenv"),
    ("docx", "python-docx"),
    ("pptx", "python-pptx"),
    ("openpyxl", "openpyxl"),
    ("rich", "Rich"),
)

OutputMode = Literal["versioned", "inplace"]

OBJECT_RESOLVERS = {
    "docx": DocxObjectResolver(),
    "pptx": PptxObjectResolver(),
    "xlsx": XlsxObjectResolver(),
}


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
    embedding_provider_factory: Callable[
        [str, int | None],
        embedding_provider.EmbeddingProvider,
    ] | None = None
    _embedding_provider: embedding_provider.EmbeddingProvider | None = field(
        default=None,
        init=False,
        repr=False,
    )

    def discover_documents(self) -> list[DocumentRef]:
        documents = discover_documents(self.config.document_roots)
        return [document for document in documents if self._is_allowed_document_path(document.path)]

    def list_documents(self) -> list[DocumentRef]:
        connection = store.ensure_ready(self.config.index_path)
        try:
            rows = store.fetch_documents(connection)
        finally:
            connection.close()
        return [
            _document_ref_from_row(row)
            for row in rows
            if self._is_allowed_document_path(Path(row["path"]))
        ]

    def get_document(self, document_id: str) -> DocumentRef:
        connection = store.ensure_ready(self.config.index_path)
        try:
            document_row = self._resolve_document_by_id_row(connection, document_id)
        finally:
            connection.close()
        document = _document_ref_from_row(document_row)
        self._ensure_allowed_document_path(document.path, action="read")
        return document

    def show_document(self, document_path: Path) -> DocumentRef:
        connection = store.ensure_ready(self.config.index_path)
        try:
            resolved_path, _ = self._require_allowed_document_path(document_path, action="show")
            document_row = self._resolve_document_row(connection, resolved_path)
        finally:
            connection.close()
        return _document_ref_from_row(document_row)

    def show_item(self, document_path: Path, item_id: str) -> ItemRef:
        connection = store.ensure_ready(self.config.index_path)
        try:
            resolved_path, _ = self._require_allowed_document_path(document_path, action="show")
            document_row, item_row = self._resolve_item_row(connection, resolved_path, item_id)
        finally:
            connection.close()
        return _item_ref_from_row(item_row)

    def resolve_document_path(self, document_id: str) -> Path:
        return self.get_document(document_id).path

    def get_document_structure(self, document_id: str) -> DocumentStructure:
        document = self.get_document(document_id)
        if document.file_type == "docx":
            units = tuple(
                StructureUnit(
                    position=block.block_index,
                    unit_type=block.block_type,
                    preview=block.preview,
                    metadata=block.metadata,
                )
                for block in docx_adapter.get_blocks(document.path)
            )
        elif document.file_type == "pptx":
            units = tuple(
                StructureUnit(
                    position=slide.slide_number,
                    unit_type="slide",
                    preview=slide.preview,
                    metadata=slide.metadata,
                )
                for slide in pptx_adapter.get_presentation_structure(document.path)
            )
        else:
            workbook_structure = xlsx_adapter.get_workbook_structure(document.path)
            units = tuple(
                StructureUnit(
                    position=sheet.position,
                    unit_type="worksheet",
                    preview=sheet.preview,
                    metadata={"sheet_name": sheet.sheet_name, **sheet.metadata},
                )
                for sheet in workbook_structure.sheets
            )

        return DocumentStructure(document=document, units=units)

    def get_structure(self, document_id: str) -> StructureCollection:
        document = self.get_document(document_id)
        if document.file_type == "docx":
            sections = docx_adapter.resolve_structure(document.path)
        elif document.file_type == "pptx":
            sections = pptx_adapter.resolve_structure(document.path)
        else:
            sections = xlsx_adapter.resolve_structure(document.path)
        return StructureCollection(document=document, sections=sections)

    def get_section(
        self,
        document_id: str,
        section_id: str,
        *,
        cell_range: str | None = None,
    ) -> SectionPayload:
        document = self.get_document(document_id)
        if document.file_type == "docx":
            return replace(docx_adapter.get_section(document.path, section_id), document=document)
        if document.file_type == "pptx":
            return replace(pptx_adapter.get_section(document.path, section_id), document=document)
        return replace(
            xlsx_adapter.get_section(document.path, section_id, cell_range=cell_range),
            document=document,
        )

    def get_node(self, document_id: str, node_id: str) -> NodePayload:
        document = self.get_document(document_id)
        if document.file_type == "docx":
            item_type, text, metadata = docx_adapter.read_node(document.path, node_id)
        elif document.file_type == "pptx":
            item_type, text, metadata = pptx_adapter.read_node(document.path, node_id)
        else:
            item_type, text, metadata = xlsx_adapter.read_node(document.path, node_id)
        return NodePayload(
            document_id=document.document_id,
            node_id=node_id,
            item_type=item_type,
            text=text,
            metadata=metadata,
        )

    def get_object(self, document_id: str, locator: str) -> ObjectPayload:
        document = self.get_document(document_id)
        source_hash = _content_hash(document.path)
        resolver = _object_resolver(document.file_type)
        try:
            payload = resolver.get_object(document.path, locator)
        except (InvalidArgumentsError, TargetNotFoundError) as exc:
            if source_hash != document.content_hash:
                raise StaleLocatorError(
                    f"stale locator: {locator} is no longer valid for {document.path}"
                ) from exc
            raise
        return replace(payload, document=document)

    def list_children(
        self,
        document_id: str,
        locator: str,
        *,
        child_type: str | None = None,
        limit: int | None = None,
    ) -> list[ChildSummary]:
        document = self.get_document(document_id)
        source_hash = _content_hash(document.path)
        resolver = _object_resolver(document.file_type)
        try:
            return resolver.list_children(
                document.path,
                locator,
                child_type=child_type,
                limit=limit,
            )
        except (InvalidArgumentsError, TargetNotFoundError) as exc:
            if source_hash != document.content_hash:
                raise StaleLocatorError(
                    f"stale locator: {locator} is no longer valid for {document.path}"
                ) from exc
            raise

    def create_object(
        self,
        document_id: str,
        parent_locator: str,
        object_type: str,
        properties: dict[str, Any],
        position: object | None = None,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self.get_document(document_id)
        self._ensure_object_locator_fresh(document, parent_locator)
        parent = self.get_object(document_id, parent_locator)
        _require_capability(parent.capabilities, Capability.ADD_CHILD, parent_locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)

        try:
            locator, summary, metadata = _create_object_on_path(
                document.path,
                document.file_type,
                parent_locator=parent_locator,
                object_type=object_type,
                properties=properties,
                position=position,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, parent_locator, exc)
            raise

        output_document = self.index_document(output_path)
        payload = self.get_object(output_document.document_id, locator)
        return MutationResult(
            document_path=document.path,
            output_path=output_path,
            document_id=output_document.document_id,
            locator=payload.locator,
            object_type=payload.object_type,
            summary=summary,
            capabilities=payload.capabilities,
            parent_locator=payload.parent_locator,
            metadata=metadata,
        )

    def update_object(
        self,
        document_id: str,
        locator: str,
        properties: dict[str, Any],
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self.get_document(document_id)
        self._ensure_object_locator_fresh(document, locator)
        current = self.get_object(document_id, locator)
        _require_capability(current.capabilities, Capability.UPDATE, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)

        try:
            summary, metadata = _update_object_on_path(
                document.path,
                document.file_type,
                locator=locator,
                properties=properties,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise

        output_document = self.index_document(output_path)
        payload = self.get_object(output_document.document_id, locator)
        return MutationResult(
            document_path=document.path,
            output_path=output_path,
            document_id=output_document.document_id,
            locator=payload.locator,
            object_type=payload.object_type,
            summary=summary,
            capabilities=payload.capabilities,
            parent_locator=payload.parent_locator,
            metadata=metadata,
        )

    def move_object(
        self,
        document_id: str,
        locator: str,
        new_parent_locator: str,
        position: object | None = None,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self.get_document(document_id)
        self._ensure_object_locator_fresh(document, locator)
        current = self.get_object(document_id, locator)
        _require_capability(current.capabilities, Capability.MOVE, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)

        try:
            moved_locator, summary, metadata = _move_object_on_path(
                document.path,
                document.file_type,
                locator=locator,
                new_parent_locator=new_parent_locator,
                position=position,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise

        output_document = self.index_document(output_path)
        payload = self.get_object(output_document.document_id, moved_locator)
        return MutationResult(
            document_path=document.path,
            output_path=output_path,
            document_id=output_document.document_id,
            locator=payload.locator,
            object_type=payload.object_type,
            summary=summary,
            capabilities=payload.capabilities,
            parent_locator=payload.parent_locator,
            metadata=metadata,
        )

    def copy_object(
        self,
        document_id: str,
        locator: str,
        target_parent_locator: str,
        position: object | None = None,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self.get_document(document_id)
        self._ensure_object_locator_fresh(document, locator)
        current = self.get_object(document_id, locator)
        _require_capability(current.capabilities, Capability.COPY, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)

        try:
            copied_locator, summary, metadata = _copy_object_on_path(
                document.path,
                document.file_type,
                locator=locator,
                target_parent_locator=target_parent_locator,
                position=position,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise

        output_document = self.index_document(output_path)
        payload = self.get_object(output_document.document_id, copied_locator)
        return MutationResult(
            document_path=document.path,
            output_path=output_path,
            document_id=output_document.document_id,
            locator=payload.locator,
            object_type=payload.object_type,
            summary=summary,
            capabilities=payload.capabilities,
            parent_locator=payload.parent_locator,
            metadata=metadata,
        )

    def batch_edit(
        self,
        document_id: str,
        operations: list[dict[str, Any]],
        *,
        output_mode: OutputMode = "versioned",
        dry_run: bool = False,
    ) -> BatchResult:
        document = self.get_document(document_id)
        self._ensure_object_locator_fresh(document, _primary_locator_for_batch(operations))
        if dry_run:
            validated = tuple(
                _validate_batch_operation(document.path, document.file_type, operation)
                for operation in operations
            )
            return BatchResult(
                document_path=document.path,
                output_path=None,
                document_id=document.document_id,
                summary=f"Validated {len(validated)} operations.",
                dry_run=True,
                operations=validated,
            )

        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        temp_work_path = _make_batch_work_path(output_path, document.path.suffix)
        shutil.copy2(document.path, temp_work_path)
        try:
            mutation_results = tuple(
                _apply_batch_operation(temp_work_path, document.file_type, operation)
                for operation in operations
            )
            os.replace(temp_work_path, output_path)
        except Exception:
            temp_work_path.unlink(missing_ok=True)
            raise

        output_document = self.index_document(output_path)
        return BatchResult(
            document_path=document.path,
            output_path=output_path,
            document_id=output_document.document_id,
            summary=f"Applied {len(mutation_results)} operations.",
            operations=mutation_results,
        )

    def delete_object(
        self,
        document_id: str,
        locator: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self.get_document(document_id)
        self._ensure_object_locator_fresh(document, locator)
        current = self.get_object(document_id, locator)
        _require_capability(current.capabilities, Capability.DELETE, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)

        try:
            summary, metadata = _delete_object_on_path(
                document.path,
                document.file_type,
                locator=locator,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise

        output_document = self.index_document(output_path)
        return MutationResult(
            document_path=document.path,
            output_path=output_path,
            document_id=output_document.document_id,
            locator=None,
            object_type=current.object_type,
            summary=summary,
            capabilities=(),
            parent_locator=current.parent_locator,
            metadata=metadata,
        )

    def docx_set_paragraph_style(
        self,
        document_id: str,
        locator: str,
        style_name: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(
            document_id,
            expected="docx",
            operation="docx_set_paragraph_style",
        )
        self._ensure_object_locator_fresh(document, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            updated_locator, summary, metadata = docx_objects.set_paragraph_style(
                document.path,
                locator,
                style_name,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, updated_locator, summary, metadata)

    def docx_insert_page_break(
        self,
        document_id: str,
        locator: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(
            document_id,
            expected="docx",
            operation="docx_insert_page_break",
        )
        self._ensure_object_locator_fresh(document, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            inserted_locator, summary, metadata = docx_objects.insert_page_break(
                document.path,
                locator,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, inserted_locator, summary, metadata)

    def docx_add_table(
        self,
        document_id: str,
        row_count: int,
        column_count: int,
        *,
        position: object | None = None,
        column_widths: list[int] | None = None,
        style_name: str | None = None,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(
            document_id,
            expected="docx",
            operation="docx_add_table",
        )
        if isinstance(position, str):
            self._ensure_object_locator_fresh(document, position)
        elif isinstance(position, dict):
            after_locator = position.get("after") or position.get("after_locator")
            if isinstance(after_locator, str):
                self._ensure_object_locator_fresh(document, after_locator)

        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            inserted_locator, summary, metadata = docx_objects.add_table(
                document.path,
                row_count,
                column_count,
                position=position,
                column_widths=column_widths,
                style_name=style_name,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            stale_locator = None
            if isinstance(position, str):
                stale_locator = position
            elif isinstance(position, dict):
                maybe_locator = position.get("after") or position.get("after_locator")
                if isinstance(maybe_locator, str):
                    stale_locator = maybe_locator
            self._raise_stale_if_document_changed(document, stale_locator or "docx:document", exc)
            raise
        return self._finalize_object_mutation(document, output_path, inserted_locator, summary, metadata)

    def docx_merge_table_cells(
        self,
        document_id: str,
        start_locator: str,
        end_locator: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(
            document_id,
            expected="docx",
            operation="docx_merge_table_cells",
        )
        self._ensure_object_locator_fresh(document, start_locator)
        self._ensure_object_locator_fresh(document, end_locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            merged_locator, summary, metadata = docx_objects.merge_table_cells(
                document.path,
                start_locator,
                end_locator,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, start_locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, merged_locator, summary, metadata)

    def pptx_add_slide(
        self,
        document_id: str,
        *,
        layout_index: int | None = None,
        layout_name: str | None = None,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(document_id, expected="pptx", operation="pptx_add_slide")
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        inserted_locator, summary, metadata = pptx_objects.add_slide(
            document.path,
            layout_index=layout_index,
            layout_name=layout_name,
            output_path=output_path,
        )
        return self._finalize_object_mutation(document, output_path, inserted_locator, summary, metadata)

    def pptx_duplicate_slide(
        self,
        document_id: str,
        locator: str,
        *,
        position: int | None = None,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(
            document_id,
            expected="pptx",
            operation="pptx_duplicate_slide",
        )
        self._ensure_object_locator_fresh(document, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            copied_locator, summary, metadata = pptx_objects.duplicate_slide(
                document.path,
                locator,
                position=position,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, copied_locator, summary, metadata)

    def pptx_set_slide_layout(
        self,
        document_id: str,
        locator: str,
        *,
        layout_index: int | None = None,
        layout_name: str | None = None,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(
            document_id,
            expected="pptx",
            operation="pptx_set_slide_layout",
        )
        self._ensure_object_locator_fresh(document, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            updated_locator, summary, metadata = pptx_objects.set_slide_layout(
                document.path,
                locator,
                layout_index=layout_index,
                layout_name=layout_name,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, updated_locator, summary, metadata)

    def pptx_add_text_shape(
        self,
        document_id: str,
        locator: str,
        text: str,
        *,
        left: int,
        top: int,
        width: int,
        height: int,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(
            document_id,
            expected="pptx",
            operation="pptx_add_text_shape",
        )
        self._ensure_object_locator_fresh(document, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            added_locator, summary, metadata = pptx_objects.add_text_shape(
                document.path,
                locator,
                text=text,
                left=left,
                top=top,
                width=width,
                height=height,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, added_locator, summary, metadata)

    def xlsx_write_range(
        self,
        document_id: str,
        locator: str,
        values: list[list[Any]],
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(document_id, expected="xlsx", operation="xlsx_write_range")
        self._ensure_object_locator_fresh(document, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            updated_locator, summary, metadata = xlsx_objects.write_range(
                document.path,
                locator,
                values,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, updated_locator, summary, metadata)

    def xlsx_insert_rows_at(
        self,
        document_id: str,
        locator: str,
        row_number: int,
        count: int,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(document_id, expected="xlsx", operation="xlsx_insert_rows")
        self._ensure_object_locator_fresh(document, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            inserted_locator, summary, metadata = xlsx_objects.insert_rows(
                document.path,
                locator,
                row_number,
                count,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, inserted_locator, summary, metadata)

    def xlsx_insert_columns(
        self,
        document_id: str,
        locator: str,
        column_index: int,
        count: int,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(
            document_id,
            expected="xlsx",
            operation="xlsx_insert_columns",
        )
        self._ensure_object_locator_fresh(document, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            inserted_locator, summary, metadata = xlsx_objects.insert_columns(
                document.path,
                locator,
                column_index,
                count,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, inserted_locator, summary, metadata)

    def xlsx_set_formula(
        self,
        document_id: str,
        locator: str,
        formula: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(document_id, expected="xlsx", operation="xlsx_set_formula")
        self._ensure_object_locator_fresh(document, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            formula_locator, summary, metadata = xlsx_objects.set_formula(
                document.path,
                locator,
                formula,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, formula_locator, summary, metadata)

    def xlsx_merge_cells(
        self,
        document_id: str,
        locator: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> MutationResult:
        document = self._require_document_type(document_id, expected="xlsx", operation="xlsx_merge_cells")
        self._ensure_object_locator_fresh(document, locator)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            merged_locator, summary, metadata = xlsx_objects.merge_cells(
                document.path,
                locator,
                output_path=output_path,
            )
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            self._raise_stale_if_document_changed(document, locator, exc)
            raise
        return self._finalize_object_mutation(document, output_path, merged_locator, summary, metadata)

    def write_node(
        self,
        document_id: str,
        node_id: str,
        content: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> NodeWriteResult:
        document = self.get_document(document_id)
        source_hash = _content_hash(document.path)
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        try:
            previous = self.get_node(document_id, node_id)
            if document.file_type == "docx":
                output_path = docx_adapter.write_node(document.path, node_id, content, output_path)
            elif document.file_type == "pptx":
                output_path = pptx_adapter.write_node(document.path, node_id, content, output_path)
            else:
                output_path = xlsx_adapter.write_node(document.path, node_id, content, output_path)
        except (InvalidArgumentsError, TargetNotFoundError, TargetNotEditableError) as exc:
            if source_hash != document.content_hash:
                raise StaleLocatorError(
                    f"stale locator: {node_id} is no longer valid for {document.path}"
                ) from exc
            raise

        output_document = self.index_document(output_path)
        new_text = self.get_node(output_document.document_id, node_id).text

        return NodeWriteResult(
            document_path=document.path,
            output_path=output_path,
            document_id=output_document.document_id,
            node_id=node_id,
            new_text=new_text,
            previous_text=previous.text,
        )

    def insert_content(
        self,
        document_id: str,
        content: str,
        *,
        style_name: str | None = None,
        after_node_id: str | None = None,
        output_mode: OutputMode = "versioned",
    ) -> InsertContentResult:
        document = self._require_document_type(document_id, expected="docx", operation="insert_content")
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        output_path, new_node_id = docx_adapter.insert_paragraph(
            document.path,
            content,
            style_name=style_name,
            after_locator=after_node_id,
            output_path=output_path,
        )
        output_document = self.index_document(output_path)
        node = self.get_node(output_document.document_id, new_node_id)
        return InsertContentResult(
            document_path=document.path,
            output_path=output_path,
            document_id=output_document.document_id,
            new_node_id=new_node_id,
            preview=node.text[:120],
        )

    def xlsx_insert_rows(
        self,
        document_id: str,
        sheet_name: str,
        *,
        rows: list[list[str]] | None = None,
        records: list[dict[str, str]] | None = None,
        output_mode: OutputMode = "versioned",
    ) -> XlsxInsertRowsResult:
        document = self._require_document_type(
            document_id,
            expected="xlsx",
            operation="xlsx_insert_rows",
        )
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        if rows is not None:
            output_path, start_row, _ = xlsx_adapter.write_table(
                document.path,
                sheet_name,
                rows=rows,
                output_path=output_path,
            )
            rows_inserted = len(rows)
        else:
            if records is None:
                raise InvalidArgumentsError("xlsx_insert_rows requires either rows or records.")
            output_path, start_row, _ = xlsx_adapter.write_table(
                document.path,
                sheet_name,
                records=records,
                output_path=output_path,
            )
            rows_inserted = len(records)
        output_document = self.index_document(output_path)
        first_row_locator = xlsx_adapter.make_item_id(sheet_name, f"A{start_row}")
        return XlsxInsertRowsResult(
            document_path=document.path,
            output_path=output_path,
            document_id=output_document.document_id,
            rows_inserted=rows_inserted,
            first_row_locator=first_row_locator,
        )

    def docx_get_tables(self, document_id: str) -> DocxTablesResult:
        document = self._require_document_type(document_id, expected="docx", operation="docx_get_tables")
        tables = tuple(
            DocxTableEntry(
                locator=docx_adapter.make_table_cell_locator(table.table_index, 0, 0),
                table_index=table.table_index,
                rows=table.rows,
                preview=table.preview,
                metadata={
                    "block_index": table.block_index,
                    **table.metadata,
                },
            )
            for table in docx_adapter.get_tables(document.path)
        )
        return DocxTablesResult(document=document, tables=tables)

    def get_presentation_structure(self, document_id: str) -> PresentationStructure:
        document = self._require_document_type(document_id, expected="pptx", operation="get_presentation_structure")
        result = pptx_adapter.get_presentation_structure(document.path)
        return PresentationStructure(document=document, slides=result)

    def get_slide_bundle(self, document_id: str, slide_number: int):
        document = self._require_document_type(document_id, expected="pptx", operation="get_slide_bundle")
        return replace(pptx_adapter.get_slide_bundle(document.path, slide_number), document=document)

    def get_slide_notes(self, document_id: str, slide_number: int) -> SlideNotes:
        document = self._require_document_type(document_id, expected="pptx", operation="get_slide_notes")
        return SlideNotes(
            document_id=document.document_id,
            slide_number=slide_number,
            notes_text=pptx_adapter.get_slide_notes(document.path, slide_number),
        )

    def get_workbook_structure(self, document_id: str) -> WorkbookStructure:
        document = self._require_document_type(document_id, expected="xlsx", operation="get_workbook_structure")
        return replace(xlsx_adapter.get_workbook_structure(document.path), document=document)

    def get_sheet_snapshot(
        self,
        document_id: str,
        sheet_name: str,
        *,
        cell_range: str | None = None,
        start_cell: str | None = None,
        row_count: int | None = None,
        column_count: int | None = None,
    ) -> SheetSnapshot:
        document = self._require_document_type(document_id, expected="xlsx", operation="get_sheet_snapshot")
        return replace(
            xlsx_adapter.get_sheet_snapshot(
                document.path,
                sheet_name,
                cell_range=cell_range,
                start_cell=start_cell,
                row_count=row_count,
                column_count=column_count,
            ),
            document=document,
        )

    def get_document_blocks(self, document_id: str) -> DocumentBlocks:
        document = self._require_document_type(document_id, expected="docx", operation="get_document_blocks")
        return DocumentBlocks(document=document, blocks=docx_adapter.get_blocks(document.path))

    def get_paragraphs(self, document_id: str) -> ParagraphCollection:
        document = self._require_document_type(document_id, expected="docx", operation="get_paragraphs")
        return ParagraphCollection(document=document, paragraphs=docx_adapter.get_paragraphs(document.path))

    def get_tables(self, document_id: str) -> TableCollection:
        document = self._require_document_type(document_id, expected="docx", operation="get_tables")
        return TableCollection(document=document, tables=docx_adapter.get_tables(document.path))

    def get_block_bundle(self, document_id: str, block_index: int) -> BlockBundle:
        document = self._require_document_type(document_id, expected="docx", operation="get_block_bundle")
        return replace(docx_adapter.get_block_bundle(document.path, block_index), document=document)

    def append_row(
        self,
        document_id: str,
        sheet_name: str,
        *,
        values: list[str] | None = None,
        record: dict[str, str] | None = None,
        output_mode: OutputMode = "versioned",
    ) -> StructuredWriteResult:
        document = self._require_document_type(document_id, expected="xlsx", operation="append_row")
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        output_path, row_number, coordinates = xlsx_adapter.append_row(
            document.path,
            sheet_name,
            values=values,
            record=record,
            output_path=output_path,
        )
        return StructuredWriteResult(
            document_path=document.path,
            output_path=output_path,
            target=StructuredTarget(
                target_type="worksheet_row",
                identifier=f"{sheet_name}!row:{row_number}",
                preview=", ".join(coordinates),
                metadata={
                    "sheet_name": sheet_name,
                    "row_number": row_number,
                    "coordinates": list(coordinates),
                },
            ),
            summary=f"Appended row {row_number} to worksheet {sheet_name}.",
        )

    def write_table(
        self,
        document_id: str,
        sheet_name: str,
        *,
        rows: list[list[str]] | None = None,
        records: list[dict[str, str]] | None = None,
        column_mapping: dict[str, str] | None = None,
        output_mode: OutputMode = "versioned",
    ) -> StructuredWriteResult:
        document = self._require_document_type(document_id, expected="xlsx", operation="write_table")
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        output_path, start_row, end_row = xlsx_adapter.write_table(
            document.path,
            sheet_name,
            rows=rows,
            records=records,
            column_mapping=column_mapping,
            output_path=output_path,
        )
        return StructuredWriteResult(
            document_path=document.path,
            output_path=output_path,
            target=StructuredTarget(
                target_type="worksheet_range",
                identifier=f"{sheet_name}!rows:{start_row}-{end_row}",
                preview=f"{sheet_name} rows {start_row}-{end_row}",
                metadata={
                    "sheet_name": sheet_name,
                    "start_row": start_row,
                    "end_row": end_row,
                    "row_count": end_row - start_row + 1,
                },
            ),
            summary=f"Wrote {end_row - start_row + 1} rows to worksheet {sheet_name}.",
        )

    def append_paragraph(
        self,
        document_id: str,
        text: str,
        *,
        style_name: str | None = None,
        output_mode: OutputMode = "versioned",
    ) -> StructuredWriteResult:
        document = self._require_document_type(document_id, expected="docx", operation="append_paragraph")
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        output_path, block_index = docx_adapter.append_paragraph_block(
            document.path,
            text,
            style_name=style_name,
            output_path=output_path,
        )
        bundle = docx_adapter.get_block_bundle(output_path, block_index)
        return StructuredWriteResult(
            document_path=document.path,
            output_path=output_path,
            target=StructuredTarget(
                target_type="document_block",
                identifier=f"block:{block_index}",
                preview=bundle.block.preview,
                metadata={
                    "block_index": block_index,
                    "block_type": bundle.block.block_type,
                    "style_name": None if bundle.paragraph is None else bundle.paragraph.style_name,
                },
            ),
            summary=f"Appended paragraph block {block_index}.",
        )

    def replace_block(
        self,
        document_id: str,
        block_index: int,
        text: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> StructuredWriteResult:
        document = self._require_document_type(document_id, expected="docx", operation="replace_block")
        output_path = self._resolve_write_output_path(document.path, output_mode=output_mode)
        output_path = docx_adapter.replace_block(
            document.path,
            block_index,
            text,
            output_path=output_path,
        )
        bundle = docx_adapter.get_block_bundle(output_path, block_index)
        return StructuredWriteResult(
            document_path=document.path,
            output_path=output_path,
            target=StructuredTarget(
                target_type="document_block",
                identifier=f"block:{block_index}",
                preview=bundle.block.preview,
                metadata={
                    "block_index": block_index,
                    "block_type": bundle.block.block_type,
                },
            ),
            summary=f"Replaced block {block_index}.",
        )

    def index_path(
        self,
        path: Path,
        *,
        with_embeddings: bool = False,
        reporter: ProgressReporter | None = None,
    ) -> IndexSummary:
        resolved_input = canonicalize_existing_path(path)
        self._ensure_allowed_document_path(resolved_input, action="index")
        candidates = _index_candidates(resolved_input)
        active_reporter = reporter or NullProgressReporter()
        indexed = 0
        skipped = 0

        active_reporter.on_index_start(len(candidates))
        for index, candidate in enumerate(candidates, start=1):
            self._ensure_allowed_document_path(candidate, action="index")
            if candidate.suffix.lower() not in INDEXABLE_EXTENSIONS:
                skipped += 1
                continue
            active_reporter.on_file_start(candidate, index, len(candidates))
            document_ref = self.index_document(
                candidate,
                with_embeddings=with_embeddings,
                reporter=active_reporter,
            )
            active_reporter.on_file_done(candidate, items_indexed=document_ref.item_count or 0)
            indexed += 1

        active_reporter.on_index_done(files_indexed=indexed, files_skipped=skipped)
        return IndexSummary(
            files_scanned=len(candidates),
            files_indexed=indexed,
            files_skipped=skipped,
        )

    def reindex_path(
        self,
        path: Path,
        *,
        with_embeddings: bool = False,
        reporter: ProgressReporter | None = None,
    ) -> IndexSummary:
        return self.index_path(path, with_embeddings=with_embeddings, reporter=reporter)

    def refresh_document(
        self,
        document_id: str,
        *,
        reporter: ProgressReporter | None = None,
    ) -> IndexSummary:
        return self.reindex_path(self.resolve_document_path(document_id), reporter=reporter)

    def index_document(
        self,
        document_path: Path,
        *,
        with_embeddings: bool = False,
        reporter: ProgressReporter | None = None,
    ) -> DocumentRef:
        active_reporter = reporter or NullProgressReporter()
        resolved_path, file_type = self._require_allowed_document_path(document_path, action="index")
        document_ref = _build_document_ref(resolved_path, file_type)
        items = _extract_items(resolved_path, file_type)
        document_ref = replace(document_ref, item_count=len(items))

        connection = store.ensure_ready(self.config.index_path)
        try:
            store.upsert_document(connection, document_ref)
            store.delete_document_embeddings(connection, document_ref.document_id)
            store.replace_document_items(connection, document_ref.document_id, items)
            if with_embeddings and items:
                provider = self._get_embedding_provider()
                store.ensure_embedding_meta(
                    connection,
                    model_name=provider.model_name,
                    dimensions=provider.dimensions,
                )
                if file_type == "xlsx":
                    row_embeddings = xlsx_adapter.build_row_embeddings(items, resolved_path)
                    embedding_texts = [row_embedding.text for row_embedding in row_embeddings]
                else:
                    row_embeddings = []
                    embedding_texts = [
                        _build_embedding_text(item, resolved_path, file_type=file_type)
                        for item in items
                    ]
                LOGGER.info(
                    "Embedding generation started for %s with %s items",
                    resolved_path,
                    len(embedding_texts),
                )
                if embedding_texts:
                    active_reporter.on_embedding_start(resolved_path, len(embedding_texts))
                    started_at = time.perf_counter()
                    blobs = provider.embed_texts(
                        embedding_texts,
                        on_progress=active_reporter.on_embedding_item,
                    )
                    if file_type == "xlsx":
                        if len(blobs) != len(row_embeddings):
                            raise RuntimeError(
                                "Embedding provider returned an unexpected number of XLSX row vectors."
                            )
                        store.replace_xlsx_row_embeddings(
                            connection,
                            document_id=document_ref.document_id,
                            model_name=provider.model_name,
                            dimensions=provider.dimensions,
                            row_embeddings=_build_xlsx_row_embedding_records(
                                document_ref.document_id,
                                row_embeddings,
                                blobs,
                            ),
                        )
                    else:
                        if len(blobs) != len(items):
                            raise RuntimeError(
                                "Embedding provider returned an unexpected number of vectors."
                            )
                        store.replace_document_embeddings(
                            connection,
                            document_id=document_ref.document_id,
                            model_name=provider.model_name,
                            dimensions=provider.dimensions,
                            embeddings=[
                                (store.make_storage_id(document_ref.document_id, item.item_id), blob)
                                for item, blob in zip(items, blobs, strict=True)
                            ],
                        )
                    LOGGER.info(
                        "Embedding generation completed for %s with %s items in %.3fs",
                        resolved_path,
                        len(embedding_texts),
                        time.perf_counter() - started_at,
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        return document_ref

    def search_corpus(
        self,
        query: str,
        *,
        file_type: str | None = None,
        document_path: Path | None = None,
        limit: int = 20,
        mode: SearchMode = "keyword",
    ) -> list[SearchHit]:
        if file_type not in (None, "docx", "pptx", "xlsx"):
            raise InvalidArgumentsError(
                "Only DOCX, PPTX, and XLSX search are supported in this feature."
            )
        normalized_mode = _normalize_search_mode(mode)

        resolved_document_path = None
        if document_path is not None:
            resolved_document_path, _ = self._require_allowed_document_path(document_path, action="search")
        connection = store.ensure_ready(self.config.index_path)
        try:
            if normalized_mode == "keyword":
                rows = store.search_items(
                    connection,
                    query,
                    file_type=file_type,
                    document_path=resolved_document_path,
                    limit=limit,
                )
                hits = [_search_hit_from_keyword_row(row) for row in rows]
            elif normalized_mode == "semantic":
                if not store.has_item_embeddings(
                    connection,
                    file_type=file_type,
                    document_path=resolved_document_path,
                ):
                    raise NoEmbeddingsError(
                        "No embeddings are indexed for the requested corpus. Reindex with --with-embeddings first."
                    )
                hits = self._semantic_search(
                    connection,
                    query,
                    file_type=file_type,
                    document_path=resolved_document_path,
                    limit=max(limit, self.config.vector_search_top_k),
                )[:limit]
            else:
                keyword_rows = store.search_items(
                    connection,
                    query,
                    file_type=file_type,
                    document_path=resolved_document_path,
                    limit=max(limit, self.config.vector_search_top_k),
                )
                semantic_hits = self._semantic_search(
                    connection,
                    query,
                    file_type=file_type,
                    document_path=resolved_document_path,
                    limit=max(limit, self.config.vector_search_top_k),
                    require_embeddings=False,
                )
                hits = _merge_hybrid_hits(
                    keyword_rows,
                    semantic_hits,
                    limit=limit,
                    keyword_weight=self.config.hybrid_keyword_weight,
                    semantic_weight=self.config.hybrid_semantic_weight,
                )
                LOGGER.info(
                    "Hybrid merge completed for query=%r with %s keyword hits, %s semantic hits, %s merged hits",
                    query,
                    len(keyword_rows),
                    len(semantic_hits),
                    len(hits),
                )
        finally:
            connection.close()

        return [
            hit
            for hit in hits
            if hit.document_path is not None and self._is_allowed_document_path(hit.document_path)
        ]

    def locate_paragraph(self, document_path: Path, paragraph_index: int) -> ItemRef:
        return self.locate_items(document_path, paragraph_index=paragraph_index)[0]

    def locate_slide_shapes(
        self,
        document_path: Path,
        slide_number: int,
        shape_id: int | None = None,
    ) -> list[ItemRef]:
        return self.locate_items(document_path, slide_number=slide_number, shape_id=shape_id)

    def locate_cell(self, document_path: Path, sheet_name: str, cell_coordinate: str) -> ItemRef:
        return self.locate_items(document_path, sheet_name=sheet_name, cell_coordinate=cell_coordinate)[0]

    def locate_items(
        self,
        document_path: Path,
        *,
        paragraph_index: int | None = None,
        slide_number: int | None = None,
        shape_id: int | None = None,
        sheet_name: str | None = None,
        cell_coordinate: str | None = None,
    ) -> list[ItemRef]:
        resolved_path, file_type = self._require_allowed_document_path(document_path, action="locate")
        connection = store.ensure_ready(self.config.index_path)
        try:
            document_row = self._resolve_document_row(connection, resolved_path)
            if file_type == "docx":
                if (
                    paragraph_index is None
                    or slide_number is not None
                    or shape_id is not None
                    or sheet_name is not None
                    or cell_coordinate is not None
                ):
                    raise InvalidArgumentsError(
                        "DOCX locate requires --paragraph and does not support --slide."
                    )
                item_row = self._resolve_indexed_item_row(
                    connection,
                    document_row,
                    f"para:{paragraph_index}",
                    resolved_path,
                )
                return [_item_ref_from_row(item_row)]

            if file_type == "pptx":
                if paragraph_index is not None or sheet_name is not None or cell_coordinate is not None:
                    raise InvalidArgumentsError(
                        "PPTX locate supports --slide and optional --shape only."
                    )
                if slide_number is None:
                    raise InvalidArgumentsError("PPTX locate requires --slide.")

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
                        raise TargetNotFoundError(
                            f"No indexed PPTX text shapes found on slide {slide_number} for {resolved_path}"
                        )
                    raise TargetNotFoundError(
                        f"No indexed PPTX text shape found for slide {slide_number} shape {shape_id} in {resolved_path}"
                    )
                return [_item_ref_from_row(row) for row in matches]

            if paragraph_index is not None or slide_number is not None or shape_id is not None:
                raise InvalidArgumentsError("XLSX locate supports --sheet and --cell only.")
            if sheet_name is None or cell_coordinate is None:
                raise InvalidArgumentsError("XLSX locate requires --sheet and --cell.")

            item_row = self._resolve_indexed_item_row(
                connection,
                document_row,
                xlsx_adapter.make_item_id(sheet_name, cell_coordinate),
                resolved_path,
            )
            return [_item_ref_from_row(item_row)]
        finally:
            connection.close()

    def read_item(self, document_path: Path, item_id: str) -> str:
        resolved_path, file_type = self._require_allowed_document_path(document_path, action="read")
        connection = store.ensure_ready(self.config.index_path)
        try:
            document_row = self._resolve_document_row(connection, resolved_path)
            self._resolve_indexed_item_row(connection, document_row, item_id, resolved_path)
        finally:
            connection.close()
        if file_type == "docx":
            return docx_adapter.read_paragraph(resolved_path, item_id)
        if file_type == "pptx":
            return pptx_adapter.read_text_shape(resolved_path, item_id)
        return xlsx_adapter.read_cell(resolved_path, item_id)

    def replace_item_text(
        self,
        document_path: Path,
        item_id: str,
        text: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> PatchResult:
        resolved_path, file_type = self._require_allowed_document_path(document_path, action="write")
        if file_type == "xlsx":
            raise InvalidArgumentsError("XLSX replace is not supported; use write-cell.")

        self._prepare_write_target(
            resolved_path,
            file_type,
            item_id,
            require_indexed_item=True,
        )
        output_path = self._resolve_write_output_path(resolved_path, output_mode=output_mode)

        if file_type == "docx":
            output_path = docx_adapter.replace_paragraph(resolved_path, item_id, text, output_path)
            updated_text = docx_adapter.read_paragraph(output_path, item_id)
        else:
            output_path = pptx_adapter.replace_text_shape(resolved_path, item_id, text, output_path)
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

    def append_item_text(
        self,
        document_path: Path,
        item_id: str,
        text: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> PatchResult:
        resolved_path, file_type = self._require_allowed_document_path(document_path, action="write")
        self._prepare_write_target(
            resolved_path,
            file_type,
            item_id,
            require_indexed_item=file_type != "xlsx",
        )
        output_path = self._resolve_write_output_path(resolved_path, output_mode=output_mode)

        if file_type == "docx":
            output_path = docx_adapter.append_paragraph(resolved_path, item_id, text, output_path)
            updated_text = docx_adapter.read_paragraph(output_path, item_id)
        elif file_type == "pptx":
            output_path = pptx_adapter.append_text_shape(resolved_path, item_id, text, output_path)
            updated_text = pptx_adapter.read_text_shape(output_path, item_id)
        else:
            output_path = xlsx_adapter.append_cell(resolved_path, item_id, text, output_path)
            updated_text = xlsx_adapter.read_cell(output_path, item_id)
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

    def write_cell_value(
        self,
        document_path: Path,
        sheet_name: str,
        cell_coordinate: str,
        value: str,
        *,
        output_mode: OutputMode = "versioned",
    ) -> PatchResult:
        resolved_path, file_type = self._require_allowed_document_path(document_path, action="write")
        if file_type != "xlsx":
            raise InvalidArgumentsError("write-cell requires an .xlsx path.")

        item_id = xlsx_adapter.make_item_id(sheet_name, cell_coordinate)
        self._prepare_write_target(
            resolved_path,
            file_type,
            item_id,
            require_indexed_item=False,
        )
        output_path = self._resolve_write_output_path(resolved_path, output_mode=output_mode)
        output_path = xlsx_adapter.write_cell(resolved_path, item_id, value, output_path)
        updated_text = xlsx_adapter.read_cell(output_path, item_id)
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

    def _prepare_write_target(
        self,
        document_path: Path,
        file_type: FileType,
        item_id: str,
        *,
        require_indexed_item: bool,
    ) -> None:
        connection = store.ensure_ready(self.config.index_path)
        try:
            document_row = self._resolve_document_row(connection, document_path)
            if require_indexed_item:
                try:
                    self._resolve_indexed_item_row(connection, document_row, item_id, document_path)
                except TargetNotFoundError:
                    if file_type == "pptx":
                        _raise_if_pptx_target_not_editable(document_path, item_id)
                    raise

            if document_row["content_hash"] != _content_hash(document_path):
                try:
                    _ensure_current_target_resolves(document_path, file_type, item_id)
                except (
                    InvalidArgumentsError,
                    TargetNotFoundError,
                    pptx_adapter.TargetNotEditableError,
                    xlsx_adapter.TargetNotAppendableError,
                ) as exc:
                    raise StaleLocatorError(
                        f"stale locator: {item_id} is no longer valid for {document_path}"
                    ) from exc
        finally:
            connection.close()

    def _ensure_object_locator_fresh(self, document: DocumentRef, locator: str | None) -> None:
        current_hash = _content_hash(document.path)
        if document.content_hash is not None and document.content_hash != current_hash:
            subject = locator or document.path.as_posix()
            raise StaleLocatorError(f"stale locator: {subject} is no longer valid for {document.path}")

    def _finalize_object_mutation(
        self,
        document: DocumentRef,
        output_path: Path,
        locator: str,
        summary: str,
        metadata: dict[str, Any],
    ) -> MutationResult:
        output_document = self.index_document(output_path)
        payload = self.get_object(output_document.document_id, locator)
        return MutationResult(
            document_path=document.path,
            output_path=output_path,
            document_id=output_document.document_id,
            locator=payload.locator,
            object_type=payload.object_type,
            summary=summary,
            capabilities=payload.capabilities,
            parent_locator=payload.parent_locator,
            metadata=metadata,
        )

    def _raise_stale_if_document_changed(
        self,
        document: DocumentRef,
        locator: str,
        exc: Exception,
    ) -> None:
        if document.content_hash is not None and document.content_hash != _content_hash(document.path):
            raise StaleLocatorError(
                f"stale locator: {locator} is no longer valid for {document.path}"
            ) from exc

    def _resolve_write_output_path(
        self,
        document_path: Path,
        *,
        output_mode: OutputMode,
    ) -> Path:
        normalized_mode = _normalize_output_mode(output_mode)
        if normalized_mode == "inplace":
            if not self.config.allow_inplace_overwrite:
                raise PolicyRefusedError(
                    "In-place overwrite is not enabled. Set allow_inplace_overwrite = true to use output-mode inplace."
                )
            self._ensure_allowed_output_path(document_path)
            return document_path

        output_path = versioning.build_versioned_output_path(
            document_path,
            output_directory=self.config.output_directory,
            create_directory=False,
        )
        self._ensure_allowed_output_path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def _require_document_type(
        self,
        document_id: str,
        *,
        expected: FileType,
        operation: str,
    ) -> DocumentRef:
        document = self.get_document(document_id)
        if document.file_type != expected:
            raise InvalidArgumentsError(
                f"{operation} requires a .{expected} document, got .{document.file_type}."
            )
        return document

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
        checks.append(_check_embedding_provider_import())
        checks.append(
            _check_embedding_model(
                self.config.embedding_model,
                self.config.embedding_dimensions,
                provider_factory=self.embedding_provider_factory,
            )
        )
        checks.append(
            _check_embedding_store(
                self.config.index_path,
                self.config.embedding_model,
                self.config.embedding_dimensions,
            )
        )
        checks.extend(_check_document_roots(self.config.document_roots))
        checks.extend(_check_allowed_roots(self.config.allowed_roots))
        checks.extend(_check_output_roots(self.config.output_roots))

        return DoctorReport(checks=tuple(checks))

    def _semantic_search(
        self,
        connection: sqlite3.Connection,
        query: str,
        *,
        file_type: str | None,
        document_path: Path | None,
        limit: int,
        require_embeddings: bool = True,
    ) -> list[SearchHit]:
        item_rows = store.fetch_item_embeddings(
            connection,
            file_type=file_type,
            document_path=document_path,
        )
        xlsx_rows = store.fetch_xlsx_row_embeddings(
            connection,
            file_type=file_type,
            document_path=document_path,
        )
        if not item_rows and not xlsx_rows:
            if require_embeddings:
                raise NoEmbeddingsError(
                    "No embeddings are indexed for the requested corpus. Reindex with --with-embeddings first."
                )
            return []

        provider = self._get_embedding_provider()
        store.ensure_embedding_meta(
            connection,
            model_name=provider.model_name,
            dimensions=provider.dimensions,
        )
        query_vector = _unpack_embedding(provider.embed_texts([query])[0], provider.dimensions)

        scored_hits: list[SearchHit] = []
        for row in item_rows:
            similarity = _cosine_similarity(
                query_vector,
                _unpack_embedding(row["embedding"], int(row["dimensions"])),
            )
            scored_hits.append(_search_hit_from_semantic_row(row, similarity))
        for row in xlsx_rows:
            similarity = _cosine_similarity(
                query_vector,
                _unpack_embedding(row["embedding"], int(row["dimensions"])),
            )
            scored_hits.append(_search_hit_from_xlsx_semantic_row(connection, row, similarity))

        scored_hits.sort(
            key=lambda hit: (
                -hit.score,
                str(hit.document_path),
                hit.item_id,
            )
        )
        LOGGER.info(
            "Semantic search executed for query=%r top_k=%s hit_count=%s",
            query,
            limit,
            min(len(scored_hits), limit),
        )
        return scored_hits[:limit]

    def _get_embedding_provider(self) -> embedding_provider.EmbeddingProvider:
        if self._embedding_provider is None:
            factory = self.embedding_provider_factory or (
                lambda model_name, dimensions: embedding_provider.LocalEmbeddingProvider(
                    model_name=model_name,
                    dimensions=dimensions,
                )
            )
            self._embedding_provider = factory(
                self.config.embedding_model,
                self.config.embedding_dimensions,
            )
        return self._embedding_provider

    def _require_allowed_document_path(
        self,
        document_path: Path,
        *,
        action: str,
    ) -> tuple[Path, FileType]:
        resolved_path, file_type = _require_indexable_path(document_path)
        self._ensure_allowed_document_path(resolved_path, action=action)
        return resolved_path, file_type

    def _ensure_allowed_document_path(self, document_path: Path, *, action: str) -> Path:
        resolved_path = canonicalize_existing_path(document_path)
        return ensure_path_allowed(
            resolved_path,
            self._read_policy_roots(),
            label=f"{action} target",
            policy_name="allowed roots",
        )

    def _ensure_allowed_output_path(self, output_path: Path) -> Path:
        resolved_output_path = canonicalize_output_path(output_path)
        return ensure_path_allowed(
            resolved_output_path,
            self.config.output_roots,
            label="write output",
            policy_name="output roots",
        )

    def _is_allowed_document_path(self, document_path: Path) -> bool:
        try:
            self._ensure_allowed_document_path(document_path, action="read")
        except (PolicyRefusedError, TargetNotFoundError):
            return False
        return True

    def _read_policy_roots(self) -> tuple[Path, ...]:
        combined = list(self.config.allowed_roots) + list(self.config.output_roots)
        unique_roots: list[Path] = []
        seen: set[Path] = set()
        for root in combined:
            if root not in seen:
                unique_roots.append(root)
                seen.add(root)
        return tuple(unique_roots)

    def _resolve_item_row(
        self,
        connection: sqlite3.Connection,
        document_path: Path,
        item_id: str,
    ) -> tuple[sqlite3.Row, sqlite3.Row]:
        resolved_path, _ = self._require_allowed_document_path(document_path, action="show")
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
            raise TargetNotFoundError(f"Document is not indexed: {document_path}")
        return document_row

    def _resolve_document_by_id_row(
        self,
        connection: sqlite3.Connection,
        document_id: str,
    ) -> sqlite3.Row:
        document_row = store.fetch_document_by_id(connection, document_id)
        if document_row is None:
            raise TargetNotFoundError(f"Document is not indexed: {document_id}")
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
            raise TargetNotFoundError(f"Item {item_id} is not indexed for {document_path}")
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
    content_hash = _content_hash(resolved)
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
    resolved = canonicalize_existing_path(path)
    file_type = INDEXABLE_EXTENSIONS.get(resolved.suffix.lower())
    if file_type is None:
        raise InvalidArgumentsError(
            f"Implemented operations require a .docx, .pptx, or .xlsx path: {path}"
        )
    return resolved, file_type


def _extract_items(document_path: Path, file_type: FileType):
    if file_type == "docx":
        return docx_adapter.extract_document(document_path)
    if file_type == "pptx":
        return pptx_adapter.extract_document(document_path)
    if file_type == "xlsx":
        return xlsx_adapter.extract_document(document_path)
    raise InvalidArgumentsError(f"Unsupported indexable file type: {file_type}")


def _search_hit_from_keyword_row(row: sqlite3.Row) -> SearchHit:
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
        match_mode="keyword",
    )


def _search_hit_from_semantic_row(row: sqlite3.Row, similarity: float) -> SearchHit:
    return SearchHit(
        document_id=row["document_id"],
        item_id=row["item_id"],
        score=similarity,
        matched_text=row["content_text"],
        locator=row["locator"],
        item_type=row["item_type"],
        preview=row["preview"],
        document_path=Path(row["path"]),
        display_name=row["display_name"],
        match_mode="semantic",
        scores={"semantic": similarity, "final": similarity},
    )


def _search_hit_from_xlsx_semantic_row(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    similarity: float,
) -> SearchHit:
    contributing_cells = store.fetch_xlsx_row_embedding_cells(connection, row["embedding_id"])
    representative_coordinate = _metadata_value(row, "coordinate")
    return SearchHit(
        document_id=row["document_id"],
        item_id=row["item_id"],
        score=similarity,
        matched_text=row["content_text"],
        locator=row["locator"],
        item_type=row["item_type"],
        preview=row["preview"],
        document_path=Path(row["path"]),
        display_name=row["display_name"],
        match_mode="semantic",
        scores={"semantic": similarity, "final": similarity},
        metadata={
            "matched_sheet": row["sheet_name"],
            "matched_row": int(row["row_number"]),
            "contributing_cell_coordinates": [
                cell["cell_coordinate"]
                for cell in contributing_cells
            ],
            "representative_cell_coordinate": representative_coordinate,
            "resolved_from_row_embedding": True,
        },
    )


def _document_ref_from_row(row: sqlite3.Row) -> DocumentRef:
    return DocumentRef(
        document_id=row["document_id"],
        path=Path(row["path"]),
        file_type=row["file_type"],
        display_name=row["display_name"],
        modified_time=float(row["modified_time"]),
        content_hash=row["content_hash"],
        item_count=None if "item_count" not in row.keys() else int(row["item_count"]),
    )


def _item_ref_from_row(row: sqlite3.Row) -> ItemRef:
    return ItemRef(
        document_id=row["document_id"],
        item_id=row["item_id"],
        item_type=row["item_type"],
        locator=row["locator"],
        preview=row["preview"],
        metadata=json.loads(row["metadata_json"]),
        content_text=row["content_text"],
    )


def _metadata_value(row: sqlite3.Row, key: str, *, default=None):
    metadata = json.loads(row["metadata_json"])
    return metadata.get(key, default)


def _normalize_search_mode(mode: str) -> SearchMode:
    normalized = mode.strip().lower()
    if normalized not in {"keyword", "semantic", "hybrid"}:
        raise InvalidArgumentsError(f"Unsupported search mode: {mode}")
    return normalized  # type: ignore[return-value]


def _normalize_output_mode(output_mode: str) -> OutputMode:
    normalized = output_mode.strip().lower()
    if normalized not in {"versioned", "inplace"}:
        raise InvalidArgumentsError(f"Unsupported output mode: {output_mode}")
    return normalized  # type: ignore[return-value]


def _content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_embedding_text(item: IndexedItem, document_path: Path, *, file_type: FileType) -> str:
    if file_type == "docx":
        return docx_adapter.build_embedding_text(item, document_path)
    if file_type == "pptx":
        return pptx_adapter.build_embedding_text(item, document_path)
    if file_type == "xlsx":
        return xlsx_adapter.build_embedding_text(item, document_path)
    raise InvalidArgumentsError(f"Unsupported embedding text type: {file_type}")


def _unpack_embedding(blob: bytes, dimensions: int) -> list[float]:
    expected_length = dimensions * 4
    if len(blob) != expected_length:
        raise RuntimeError(
            f"Embedding blob length {len(blob)} does not match expected size {expected_length}."
        )
    return list(struct.unpack(f"<{dimensions}f", blob))


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise RuntimeError("Embedding vectors must have the same dimensionality.")
    return float(sum(a * b for a, b in zip(left, right)))


def _rank_scores(storage_ids: Sequence[str]) -> dict[str, float]:
    return {
        storage_id: 1.0 / rank
        for rank, storage_id in enumerate(storage_ids, start=1)
    }


def _merge_hybrid_hits(
    keyword_rows: Sequence[sqlite3.Row],
    semantic_hits: Sequence[SearchHit],
    *,
    limit: int,
    keyword_weight: float,
    semantic_weight: float,
) -> list[SearchHit]:
    keyword_by_storage = {row["storage_id"]: row for row in keyword_rows}
    semantic_by_storage = {
        f"{hit.document_id}:{hit.item_id}": hit
        for hit in semantic_hits
    }
    keyword_rank_scores = _rank_scores([row["storage_id"] for row in keyword_rows])
    semantic_rank_scores = _rank_scores(
        [f"{hit.document_id}:{hit.item_id}" for hit in semantic_hits]
    )

    merged: list[SearchHit] = []
    for storage_id in sorted(set(keyword_by_storage) | set(semantic_by_storage)):
        keyword_row = keyword_by_storage.get(storage_id)
        semantic_hit = semantic_by_storage.get(storage_id)
        base_hit = semantic_hit if semantic_hit is not None else _search_hit_from_keyword_row(keyword_row)  # type: ignore[arg-type]
        keyword_score = keyword_rank_scores.get(storage_id, 0.0)
        semantic_score = semantic_rank_scores.get(storage_id, 0.0)
        final_score = (keyword_weight * keyword_score) + (semantic_weight * semantic_score)
        merged.append(
            SearchHit(
                document_id=base_hit.document_id,
                item_id=base_hit.item_id,
                score=final_score,
                matched_text=base_hit.matched_text,
                locator=base_hit.locator,
                item_type=base_hit.item_type,
                preview=base_hit.preview,
                document_path=base_hit.document_path,
                display_name=base_hit.display_name,
                match_mode="hybrid",
                scores={
                    "keyword": keyword_score,
                    "semantic": semantic_score,
                    "final": final_score,
                },
                metadata=dict(base_hit.metadata),
            )
        )

    merged.sort(
        key=lambda hit: (
            -hit.score,
            -(hit.scores or {}).get("semantic", 0.0),
            -(hit.scores or {}).get("keyword", 0.0),
            str(hit.document_path),
            hit.item_id,
        )
    )
    return merged[:limit]


def _ensure_current_target_resolves(document_path: Path, file_type: FileType, item_id: str) -> None:
    if file_type == "docx":
        docx_adapter.read_paragraph(document_path, item_id)
        return
    if file_type == "pptx":
        pptx_adapter.read_text_shape(document_path, item_id)
        return
    xlsx_adapter.read_cell(document_path, item_id)


def _object_resolver(file_type: FileType):
    return OBJECT_RESOLVERS[file_type]


def _require_capability(
    capabilities: Sequence[Capability],
    required: Capability,
    locator: str,
) -> None:
    if required not in capabilities:
        raise TargetNotEditableError(f"{locator} does not support {required.value}.")


def _primary_locator_for_batch(operations: Sequence[dict[str, Any]]) -> str | None:
    for operation in operations:
        for key in ("locator", "parent_locator", "new_parent_locator", "target_parent_locator"):
            value = operation.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _make_batch_work_path(output_path: Path, suffix: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix=".offagent-batch-",
        suffix=suffix,
        dir=output_path.parent,
        delete=False,
    )
    handle.close()
    return Path(handle.name)


def _validate_batch_operation(
    document_path: Path,
    file_type: FileType,
    operation: dict[str, Any],
) -> MutationResult:
    operation_name = _operation_name(operation)
    if operation_name == "create_object":
        parent = _object_resolver(file_type).get_object(document_path, str(operation["parent_locator"]))
        _require_capability(parent.capabilities, Capability.ADD_CHILD, parent.locator)
        _validate_create_operation(file_type, operation)
        return MutationResult(
            document_path=document_path,
            output_path=None,
            document_id=document_path.resolve().as_posix(),
            locator=None,
            object_type=str(operation["object_type"]),
            summary=f"Validated {operation_name}.",
            parent_locator=parent.locator,
            metadata={"operation": operation_name},
        )

    locator = str(operation["locator"])
    payload = _object_resolver(file_type).get_object(document_path, locator)
    required_capability = {
        "update_object": Capability.UPDATE,
        "move_object": Capability.MOVE,
        "copy_object": Capability.COPY,
    }[operation_name]
    _require_capability(payload.capabilities, required_capability, locator)
    return MutationResult(
        document_path=document_path,
        output_path=None,
        document_id=document_path.resolve().as_posix(),
        locator=payload.locator,
        object_type=payload.object_type,
        summary=f"Validated {operation_name}.",
        capabilities=payload.capabilities,
        parent_locator=payload.parent_locator,
        metadata={"operation": operation_name},
    )


def _apply_batch_operation(
    document_path: Path,
    file_type: FileType,
    operation: dict[str, Any],
) -> MutationResult:
    operation_name = _operation_name(operation)
    if operation_name == "create_object":
        locator, summary, metadata = _create_object_on_path(
            document_path,
            file_type,
            parent_locator=str(operation["parent_locator"]),
            object_type=str(operation["object_type"]),
            properties=dict(operation.get("properties", {})),
            position=operation.get("position"),
            output_path=document_path,
        )
        payload = _object_resolver(file_type).get_object(document_path, locator)
        return MutationResult(
            document_path=document_path,
            output_path=document_path,
            document_id=document_path.resolve().as_posix(),
            locator=payload.locator,
            object_type=payload.object_type,
            summary=summary,
            capabilities=payload.capabilities,
            parent_locator=payload.parent_locator,
            metadata=metadata,
        )

    if operation_name == "update_object":
        locator = str(operation["locator"])
        summary, metadata = _update_object_on_path(
            document_path,
            file_type,
            locator=locator,
            properties=dict(operation.get("properties", {})),
            output_path=document_path,
        )
        payload = _object_resolver(file_type).get_object(document_path, locator)
        return MutationResult(
            document_path=document_path,
            output_path=document_path,
            document_id=document_path.resolve().as_posix(),
            locator=payload.locator,
            object_type=payload.object_type,
            summary=summary,
            capabilities=payload.capabilities,
            parent_locator=payload.parent_locator,
            metadata=metadata,
        )

    if operation_name == "move_object":
        moved_locator, summary, metadata = _move_object_on_path(
            document_path,
            file_type,
            locator=str(operation["locator"]),
            new_parent_locator=str(operation["new_parent_locator"]),
            position=operation.get("position"),
            output_path=document_path,
        )
        payload = _object_resolver(file_type).get_object(document_path, moved_locator)
        return MutationResult(
            document_path=document_path,
            output_path=document_path,
            document_id=document_path.resolve().as_posix(),
            locator=payload.locator,
            object_type=payload.object_type,
            summary=summary,
            capabilities=payload.capabilities,
            parent_locator=payload.parent_locator,
            metadata=metadata,
        )

    copied_locator, summary, metadata = _copy_object_on_path(
        document_path,
        file_type,
        locator=str(operation["locator"]),
        target_parent_locator=str(operation["target_parent_locator"]),
        position=operation.get("position"),
        output_path=document_path,
    )
    payload = _object_resolver(file_type).get_object(document_path, copied_locator)
    return MutationResult(
        document_path=document_path,
        output_path=document_path,
        document_id=document_path.resolve().as_posix(),
        locator=payload.locator,
        object_type=payload.object_type,
        summary=summary,
        capabilities=payload.capabilities,
        parent_locator=payload.parent_locator,
        metadata=metadata,
    )


def _create_object_on_path(
    document_path: Path,
    file_type: FileType,
    *,
    parent_locator: str,
    object_type: str,
    properties: dict[str, Any],
    position: object | None,
    output_path: Path,
) -> tuple[str, str, dict[str, Any]]:
    parent = _object_resolver(file_type).get_object(document_path, parent_locator)
    _require_capability(parent.capabilities, Capability.ADD_CHILD, parent_locator)
    _validate_create_operation(
        file_type,
        {
            "parent_locator": parent_locator,
            "object_type": object_type,
            "properties": properties,
            "position": position,
        },
    )

    if file_type != "docx":
        raise InvalidArgumentsError(f"create_object is not supported for {file_type} {object_type}.")

    style_name = properties.get("style_name")
    style = None if style_name is None else str(style_name)
    text = _required_string_property(properties, ("text",), object_type)
    after_locator = _docx_after_locator(position)
    target_path, new_node_id = docx_adapter.insert_paragraph(
        document_path,
        text,
        style_name=style,
        after_locator=after_locator,
        output_path=output_path,
    )
    return (
        to_v2_locator(new_node_id, file_type="docx"),
        f"Created {object_type} under {parent_locator}.",
        {"text": text, "style_name": style, "document_path": str(target_path)},
    )


def _update_object_on_path(
    document_path: Path,
    file_type: FileType,
    *,
    locator: str,
    properties: dict[str, Any],
    output_path: Path,
) -> tuple[str, dict[str, Any]]:
    payload = _object_resolver(file_type).get_object(document_path, locator)
    _require_capability(payload.capabilities, Capability.UPDATE, locator)

    if file_type in {"docx", "pptx"}:
        content = _required_string_property(properties, ("text", "value"), payload.object_type)
        legacy_locator = to_legacy_locator(locator, file_type=file_type)
        if file_type == "docx":
            docx_adapter.write_node(document_path, legacy_locator, content, output_path)
        else:
            pptx_adapter.write_node(document_path, legacy_locator, content, output_path)
        return (f"Updated {payload.object_type} {locator}.", {"text": content})

    content = _required_string_property(properties, ("value", "text"), payload.object_type)
    legacy_locator = to_legacy_locator(locator, file_type="xlsx")
    xlsx_adapter.write_node(document_path, legacy_locator, content, output_path)
    return (f"Updated {payload.object_type} {locator}.", {"value": content})


def _move_object_on_path(
    document_path: Path,
    file_type: FileType,
    *,
    locator: str,
    new_parent_locator: str,
    position: object | None,
    output_path: Path,
) -> tuple[str, str, dict[str, Any]]:
    payload = _object_resolver(file_type).get_object(document_path, locator)
    _require_capability(payload.capabilities, Capability.MOVE, locator)

    if file_type != "pptx" or payload.object_type != "slide":
        raise InvalidArgumentsError(f"move_object is not supported for {payload.object_type}.")
    if new_parent_locator != "pptx:presentation":
        raise InvalidArgumentsError("PPTX slides can only be moved within the presentation root.")

    slide_number = _pptx_slide_number(locator)
    new_position = _required_position(position)
    _move_pptx_slide(document_path, slide_number, new_position, output_path)
    return (
        f"pptx:slide:{new_position}",
        f"Moved slide {slide_number} to position {new_position}.",
        {"previous_locator": locator, "new_parent_locator": new_parent_locator},
    )


def _copy_object_on_path(
    document_path: Path,
    file_type: FileType,
    *,
    locator: str,
    target_parent_locator: str,
    position: object | None,
    output_path: Path,
) -> tuple[str, str, dict[str, Any]]:
    payload = _object_resolver(file_type).get_object(document_path, locator)
    _require_capability(payload.capabilities, Capability.COPY, locator)

    if file_type != "pptx" or payload.object_type != "slide":
        raise InvalidArgumentsError(f"copy_object is not supported for {payload.object_type}.")
    if target_parent_locator != "pptx:presentation":
        raise InvalidArgumentsError("PPTX slides can only be copied within the presentation root.")

    slide_number = _pptx_slide_number(locator)
    copied_position = _copy_pptx_slide(document_path, slide_number, position, output_path)
    return (
        f"pptx:slide:{copied_position}",
        f"Copied slide {slide_number} to position {copied_position}.",
        {"source_locator": locator, "target_parent_locator": target_parent_locator},
    )


def _delete_object_on_path(
    document_path: Path,
    file_type: FileType,
    *,
    locator: str,
    output_path: Path,
) -> tuple[str, dict[str, Any]]:
    payload = _object_resolver(file_type).get_object(document_path, locator)
    _require_capability(payload.capabilities, Capability.DELETE, locator)

    if file_type == "docx":
        return _delete_docx_object(document_path, locator, output_path)
    if file_type == "pptx":
        return _delete_pptx_object(document_path, locator, output_path)
    return _delete_xlsx_object(document_path, locator, output_path)


def _validate_create_operation(file_type: FileType, operation: dict[str, Any]) -> None:
    object_type = str(operation["object_type"])
    if file_type != "docx" or object_type != "paragraph":
        raise InvalidArgumentsError(f"create_object does not support {file_type} {object_type}.")
    _required_string_property(dict(operation.get("properties", {})), ("text",), object_type)
    _docx_after_locator(operation.get("position"))


def _operation_name(operation: dict[str, Any]) -> str:
    raw = operation.get("operation") or operation.get("op")
    if not isinstance(raw, str) or raw not in {
        "create_object",
        "update_object",
        "move_object",
        "copy_object",
    }:
        raise InvalidArgumentsError(f"Unsupported batch operation: {raw}")
    return raw


def _required_string_property(
    properties: dict[str, Any],
    keys: Sequence[str],
    object_type: str,
) -> str:
    for key in keys:
        value = properties.get(key)
        if value is None:
            continue
        return str(value)
    raise InvalidArgumentsError(f"{object_type} updates require one of: {', '.join(keys)}.")


def _docx_after_locator(position: object | None) -> str | None:
    if position is None:
        return None
    if isinstance(position, str):
        return to_legacy_locator(position, file_type="docx")
    if isinstance(position, dict):
        for key in ("after", "after_locator"):
            after_locator = position.get(key)
            if after_locator is not None:
                return to_legacy_locator(str(after_locator), file_type="docx")
    raise InvalidArgumentsError("DOCX create_object position must be an after locator.")


def _required_position(position: object | None) -> int:
    if isinstance(position, int):
        return position
    if isinstance(position, dict):
        for key in ("index", "position"):
            value = position.get(key)
            if isinstance(value, int):
                return value
    raise InvalidArgumentsError("Move/copy operations require an integer position.")


def _pptx_slide_number(locator: str) -> int:
    canonical = to_v2_locator(locator, file_type="pptx")
    parts = canonical.split(":")
    if len(parts) != 3 or parts[:2] != ["pptx", "slide"]:
        raise InvalidArgumentsError(f"Unsupported PPTX slide locator: {locator}")
    return int(parts[2])


def _move_pptx_slide(
    document_path: Path,
    slide_number: int,
    new_position: int,
    output_path: Path,
) -> None:
    presentation = pptx_adapter._open_presentation(document_path)
    slide_count = len(presentation.slides)
    if slide_number < 1 or slide_number > slide_count:
        raise TargetNotFoundError(f"Slide {slide_number} does not exist in the presentation.")
    if new_position < 1 or new_position > slide_count:
        raise InvalidArgumentsError(f"Invalid target slide position: {new_position}")

    sld_id_list = presentation.slides._sldIdLst
    slide_id = sld_id_list.sldId_lst[slide_number - 1]
    sld_id_list.remove(slide_id)
    sld_id_list.insert(new_position - 1, slide_id)
    presentation.save(output_path)


def _copy_pptx_slide(
    document_path: Path,
    slide_number: int,
    position: object | None,
    output_path: Path,
) -> int:
    presentation = pptx_adapter._open_presentation(document_path)
    source_slide = pptx_adapter._resolve_slide(presentation, slide_number)
    new_slide = presentation.slides.add_slide(source_slide.slide_layout)

    for placeholder_shape in list(new_slide.shapes):
        placeholder_shape.element.getparent().remove(placeholder_shape.element)

    for shape in source_slide.shapes:
        new_slide.shapes._spTree.insert_element_before(deepcopy(shape.element), "p:extLst")

    for rel in source_slide.part.rels.values():
        if rel.reltype.endswith("/notesSlide") or rel.reltype.endswith("/slideLayout"):
            continue
        if rel.is_external:
            new_rid = new_slide.part.relate_to(rel.target_ref, rel.reltype, is_external=True)
        else:
            new_rid = new_slide.part.relate_to(rel.target_part, rel.reltype)
        _retarget_shape_relationships(new_slide, rel.rId, new_rid)

    if getattr(source_slide, "notes_slide", None) is not None:
        source_notes = getattr(source_slide.notes_slide, "notes_text_frame", None)
        target_notes = getattr(new_slide.notes_slide, "notes_text_frame", None)
        if source_notes is not None and target_notes is not None:
            target_notes.text = source_notes.text

    copied_position = len(presentation.slides) if position is None else _required_position(position)
    _move_pptx_slide_in_memory(presentation, len(presentation.slides), copied_position)
    presentation.save(output_path)
    return copied_position


def _move_pptx_slide_in_memory(presentation, slide_number: int, new_position: int) -> None:
    slide_count = len(presentation.slides)
    if new_position < 1 or new_position > slide_count:
        raise InvalidArgumentsError(f"Invalid target slide position: {new_position}")
    sld_id_list = presentation.slides._sldIdLst
    slide_id = sld_id_list.sldId_lst[slide_number - 1]
    sld_id_list.remove(slide_id)
    sld_id_list.insert(new_position - 1, slide_id)


def _retarget_shape_relationships(slide, source_rid: str, target_rid: str) -> None:
    for shape in slide.shapes:
        for element in shape.element.iter():
            for attr_name, attr_value in list(element.attrib.items()):
                if attr_value == source_rid:
                    element.set(attr_name, target_rid)


def _delete_docx_object(
    document_path: Path,
    locator: str,
    output_path: Path,
) -> tuple[str, dict[str, Any]]:
    canonical = to_v2_locator(locator, file_type="docx")
    if canonical.startswith("docx:para:"):
        document = docx_adapter._open_document(document_path)
        paragraph = docx_adapter._resolve_paragraph(document, to_legacy_locator(canonical, file_type="docx"))
        paragraph._element.getparent().remove(paragraph._element)
        document.save(output_path)
        return (f"Deleted paragraph {locator}.", {"locator": locator})
    if canonical.startswith("docx:table:") and ":row:" not in canonical:
        document = docx_adapter._open_document(document_path)
        parts = canonical.split(":")
        table_index = int(parts[2])
        resolved = docx_adapter._resolve_locator(document, f"table:{table_index}:cell:0:0")
        resolved.table._element.getparent().remove(resolved.table._element)
        document.save(output_path)
        return (f"Deleted table {locator}.", {"locator": locator})
    raise InvalidArgumentsError(f"delete_object is not supported for {locator}.")


def _delete_pptx_object(
    document_path: Path,
    locator: str,
    output_path: Path,
) -> tuple[str, dict[str, Any]]:
    canonical = to_v2_locator(locator, file_type="pptx")
    presentation = pptx_adapter._open_presentation(document_path)
    parts = canonical.split(":")

    if canonical.startswith("pptx:slide:") and len(parts) == 3:
        slide_number = int(parts[2])
        slide_id = presentation.slides._sldIdLst.sldId_lst[slide_number - 1]
        presentation.part.drop_rel(slide_id.rId)
        presentation.slides._sldIdLst.remove(slide_id)
        presentation.save(output_path)
        return (f"Deleted slide {locator}.", {"locator": locator})

    if len(parts) == 5 and parts[:2] == ["pptx", "slide"]:
        slide = pptx_adapter._resolve_slide(presentation, int(parts[2]))
        shape = pptx_adapter._resolve_shape(presentation, to_legacy_locator(canonical, file_type="pptx"))
        shape.element.getparent().remove(shape.element)
        presentation.save(output_path)
        return (f"Deleted {parts[3]} {locator}.", {"locator": locator, "slide_number": int(parts[2])})

    raise InvalidArgumentsError(f"delete_object is not supported for {locator}.")


def _delete_xlsx_object(
    document_path: Path,
    locator: str,
    output_path: Path,
) -> tuple[str, dict[str, Any]]:
    canonical = to_v2_locator(locator, file_type="xlsx")
    workbook = xlsx_adapter._open_workbook(document_path)
    parts = parse_locator(canonical).components

    if parts == ("xlsx", "workbook"):
        raise TargetNotEditableError(f"{locator} does not support delete.")

    if len(parts) == 3 and parts[:2] == ("xlsx", "sheet"):
        worksheet = workbook[parts[2]]
        if len(workbook.worksheets) <= 1:
            raise TargetNotEditableError(f"{locator} does not support delete.")
        workbook.remove(worksheet)
        workbook.save(output_path)
        return (f"Deleted worksheet {locator}.", {"locator": locator})

    if len(parts) == 5 and parts[:2] == ("xlsx", "sheet") and parts[3] == "row":
        worksheet = workbook[parts[2]]
        worksheet.delete_rows(int(parts[4]), 1)
        workbook.save(output_path)
        return (f"Deleted row {locator}.", {"locator": locator})

    if len(parts) == 5 and parts[:2] == ("xlsx", "sheet") and parts[3] == "col":
        worksheet = workbook[parts[2]]
        worksheet.delete_cols(int(parts[4]), 1)
        workbook.save(output_path)
        return (f"Deleted column {locator}.", {"locator": locator})

    if len(parts) == 4 and parts[:2] == ("xlsx", "sheet"):
        worksheet = workbook[parts[2]]
        coordinate = parts[3]
        if ":" in coordinate:
            for row in worksheet[coordinate]:
                for cell in row:
                    cell.value = None
            workbook.save(output_path)
            return (f"Cleared range {locator}.", {"locator": locator})
        worksheet[coordinate].value = None
        workbook.save(output_path)
        return (f"Cleared cell {locator}.", {"locator": locator})

    raise InvalidArgumentsError(f"delete_object is not supported for {locator}.")


def _build_xlsx_row_embedding_records(
    document_id: str,
    row_embeddings: Sequence[XlsxRowEmbedding],
    blobs: Sequence[bytes],
) -> list[
    tuple[
        str,
        str,
        int,
        str,
        str,
        str,
        bytes,
        list[tuple[str, str, int, bool]],
    ]
]:
    records: list[
        tuple[
            str,
            str,
            int,
            str,
            str,
            str,
            bytes,
            list[tuple[str, str, int, bool]],
        ]
    ] = []
    for row_embedding, blob in zip(row_embeddings, blobs, strict=True):
        embedding_id = store.make_xlsx_row_embedding_id(
            document_id,
            row_embedding.sheet_name,
            row_embedding.row_number,
        )
        representative_storage_id = store.make_storage_id(
            document_id,
            row_embedding.representative_item_id,
        )
        contributing_cells = [
            (
                store.make_storage_id(document_id, cell.item_id),
                cell.coordinate,
                index,
                cell.item_id == row_embedding.representative_item_id,
            )
            for index, cell in enumerate(row_embedding.contributing_cells, start=1)
        ]
        records.append(
            (
                embedding_id,
                row_embedding.sheet_name,
                row_embedding.row_number,
                representative_storage_id,
                row_embedding.text,
                row_embedding.preview,
                blob,
                contributing_cells,
            )
        )
    return records


def _raise_if_pptx_target_not_editable(document_path: Path, item_id: str) -> None:
    try:
        pptx_adapter.resolve_shape(document_path, item_id)
    except pptx_adapter.TargetNotEditableError:
        raise
    except (TargetNotFoundError, InvalidArgumentsError):
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


def _check_embedding_provider_import() -> DoctorCheck:
    try:
        importlib.import_module("offagent.adapters.embedding_provider")
    except Exception as exc:
        return DoctorCheck("Embedding Provider", False, f"Import failed: {exc}")
    return DoctorCheck("Embedding Provider", True, "Import succeeded.")


def _check_embedding_model(
    model_name: str,
    dimensions: int,
    *,
    provider_factory: Callable[[str, int | None], embedding_provider.EmbeddingProvider] | None = None,
) -> DoctorCheck:
    try:
        factory = provider_factory or (
            lambda selected_model, selected_dimensions: embedding_provider.LocalEmbeddingProvider(
                model_name=selected_model,
                dimensions=selected_dimensions,
            )
        )
        provider = factory(model_name, dimensions)
    except Exception as exc:
        return DoctorCheck("Embedding Model", False, f"Model load failed: {exc}")
    return DoctorCheck(
        "Embedding Model",
        True,
        f"Loaded {provider.model_name} with {provider.dimensions} dimensions.",
    )


def _check_embedding_store(index_path: Path, model_name: str, dimensions: int) -> DoctorCheck:
    try:
        connection = store.ensure_ready(index_path)
    except (OSError, sqlite3.Error, store.StoreCapabilityError) as exc:
        return DoctorCheck("Embedding Store", False, f"Store check failed: {exc}")

    try:
        meta = store.fetch_embedding_meta(connection)
        if not meta:
            return DoctorCheck("Embedding Store", True, "Embedding sidecar tables are ready.")
        store.ensure_embedding_meta(
            connection,
            model_name=model_name,
            dimensions=dimensions,
        )
    except Exception as exc:
        return DoctorCheck("Embedding Store", False, f"Metadata check failed: {exc}")
    finally:
        connection.close()
    return DoctorCheck("Embedding Store", True, "Embedding tables and metadata are consistent.")


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


def _check_allowed_roots(roots: Sequence[Path]) -> list[DoctorCheck]:
    if not roots:
        return [DoctorCheck("Allowed Roots", True, "No allowed-root policy configured.")]
    return _check_resolved_roots("Allowed Root", normalize_roots(roots), require_writable=False)


def _check_output_roots(roots: Sequence[Path]) -> list[DoctorCheck]:
    if not roots:
        return [DoctorCheck("Output Roots", True, "No output-root policy configured.")]
    return _check_resolved_roots("Output Root", normalize_roots(roots), require_writable=True)


def _check_resolved_roots(
    label: str,
    roots: Sequence[Path],
    *,
    require_writable: bool,
) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    for root in roots:
        if root.exists():
            if not root.is_dir():
                checks.append(DoctorCheck(f"{label} {root}", False, "Path is not a directory."))
                continue
            if require_writable and not os.access(root, os.W_OK):
                checks.append(DoctorCheck(f"{label} {root}", False, "Directory is not writable."))
                continue
            if not require_writable and not os.access(root, os.R_OK):
                checks.append(DoctorCheck(f"{label} {root}", False, "Directory is not readable."))
                continue
            checks.append(DoctorCheck(f"{label} {root}", True, "Policy root is usable."))
            continue

        existing_parent = _nearest_existing_parent(root)
        access_mode = os.W_OK if require_writable else os.R_OK
        if existing_parent is not None and os.access(existing_parent, access_mode):
            checks.append(
                DoctorCheck(f"{label} {root}", True, f"Parent path {existing_parent} is accessible.")
            )
            continue
        checks.append(
            DoctorCheck(
                f"{label} {root}",
                False,
                "Path does not exist and no accessible parent directory was found.",
            )
        )
    return checks


def _nearest_existing_parent(path: Path) -> Path | None:
    current = path
    while True:
        if current.exists():
            return current
        if current.parent == current:
            return None
        current = current.parent
