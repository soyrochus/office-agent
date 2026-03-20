from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from offagent.app.services import IndexSummary, OutputMode, PatchResult
from offagent.domain.models import DocumentRef, FileType, ItemRef, SearchHit, SearchMode


class MCPModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentModel(MCPModel):
    document_id: str
    path: str
    file_type: FileType
    display_name: str
    modified_time: float
    content_hash: str | None = None
    item_count: int | None = None

    @classmethod
    def from_document_ref(cls, document: DocumentRef) -> "DocumentModel":
        return cls(
            document_id=document.document_id,
            path=str(document.path),
            file_type=document.file_type,
            display_name=document.display_name,
            modified_time=document.modified_time,
            content_hash=document.content_hash,
            item_count=document.item_count,
        )


class ItemModel(MCPModel):
    document_id: str
    item_id: str
    item_type: str
    locator: str
    preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_item_ref(cls, item: ItemRef) -> "ItemModel":
        return cls(
            document_id=item.document_id,
            item_id=item.item_id,
            item_type=item.item_type,
            locator=item.locator,
            preview=item.preview,
            metadata=item.metadata,
        )


class SearchHitModel(MCPModel):
    document_id: str
    item_id: str
    score: float
    matched_text: str
    locator: str
    item_type: str
    preview: str
    document_path: str | None = None
    display_name: str | None = None
    match_mode: str | None = None
    scores: dict[str, float] | None = None

    @classmethod
    def from_search_hit(cls, hit: SearchHit) -> "SearchHitModel":
        return cls(
            document_id=hit.document_id,
            item_id=hit.item_id,
            score=hit.score,
            matched_text=hit.matched_text,
            locator=hit.locator,
            item_type=hit.item_type,
            preview=hit.preview,
            document_path=None if hit.document_path is None else str(hit.document_path),
            display_name=hit.display_name,
            match_mode=hit.match_mode,
            scores=hit.scores,
        )


class IndexPathResult(MCPModel):
    path: str
    files_scanned: int
    files_indexed: int
    files_skipped: int

    @classmethod
    def from_index_summary(cls, path: Path, summary: IndexSummary) -> "IndexPathResult":
        return cls(
            path=str(path),
            files_scanned=summary.files_scanned,
            files_indexed=summary.files_indexed,
            files_skipped=summary.files_skipped,
        )


class IndexDocumentsResult(MCPModel):
    files_scanned: int
    files_indexed: int
    files_skipped: int
    results: list[IndexPathResult]

    @classmethod
    def from_results(cls, results: list[IndexPathResult]) -> "IndexDocumentsResult":
        return cls(
            files_scanned=sum(result.files_scanned for result in results),
            files_indexed=sum(result.files_indexed for result in results),
            files_skipped=sum(result.files_skipped for result in results),
            results=results,
        )


class RefreshDocumentResult(MCPModel):
    document: DocumentModel
    files_scanned: int
    files_indexed: int
    files_skipped: int

    @classmethod
    def from_refresh(cls, document: DocumentRef, summary: IndexSummary) -> "RefreshDocumentResult":
        return cls(
            document=DocumentModel.from_document_ref(document),
            files_scanned=summary.files_scanned,
            files_indexed=summary.files_indexed,
            files_skipped=summary.files_skipped,
        )


class ListDocumentsResult(MCPModel):
    documents: list[DocumentModel]

    @classmethod
    def from_documents(cls, documents: list[DocumentRef]) -> "ListDocumentsResult":
        return cls(documents=[DocumentModel.from_document_ref(document) for document in documents])


class SearchDocumentsResult(MCPModel):
    hits: list[SearchHitModel]

    @classmethod
    def from_hits(cls, hits: list[SearchHit]) -> "SearchDocumentsResult":
        return cls(hits=[SearchHitModel.from_search_hit(hit) for hit in hits])


class LocateItemResult(MCPModel):
    item: ItemModel

    @classmethod
    def from_item(cls, item: ItemRef) -> "LocateItemResult":
        return cls(item=ItemModel.from_item_ref(item))


class ReadItemResult(MCPModel):
    document_id: str
    item_id: str
    text: str


class WriteResult(MCPModel):
    document_path: str
    output_path: str
    item: ItemModel
    text: str

    @classmethod
    def from_patch_result(cls, result: PatchResult) -> "WriteResult":
        return cls(
            document_path=str(result.document_path),
            output_path=str(result.output_path),
            item=ItemModel.from_item_ref(result.item),
            text=result.text,
        )


class IndexDocumentsRequest(MCPModel):
    paths: list[str] = Field(min_length=1)


class RefreshDocumentRequest(MCPModel):
    document_id: str = Field(min_length=1)


class SearchDocumentsRequest(MCPModel):
    query: str = Field(min_length=1)
    file_type: FileType | None = None
    document_id: str | None = None
    mode: SearchMode = "keyword"
    limit: int = Field(default=20, ge=1, le=100)


class LocateItemRequest(MCPModel):
    document_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class ReadItemRequest(MCPModel):
    document_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)


class ReplaceTextRequest(MCPModel):
    document_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    new_text: str
    output_mode: OutputMode = "versioned"


class AppendTextRequest(MCPModel):
    document_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    text_to_add: str
    output_mode: OutputMode = "versioned"


class WriteCellRequest(MCPModel):
    document_id: str = Field(min_length=1)
    sheet: str = Field(min_length=1)
    cell: str = Field(min_length=1)
    value: str
    output_mode: OutputMode = "versioned"
