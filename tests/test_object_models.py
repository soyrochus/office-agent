from __future__ import annotations

from pathlib import Path

from offagent.domain.models import (
    BatchResult,
    Capability,
    ChildSummary,
    DocumentRef,
    MutationResult,
    ObjectPayload,
)
from offagent.objects import ObjectResolver


def test_capability_enum_values_match_spec() -> None:
    assert tuple(capability.value for capability in Capability) == (
        "read",
        "update",
        "delete",
        "add_child",
        "move",
        "copy",
        "style",
    )


def test_object_payload_defaults() -> None:
    document = DocumentRef(
        document_id="doc-1",
        path=Path("/tmp/example.docx"),
        file_type="docx",
        display_name="example.docx",
        modified_time=1.0,
    )
    child = ChildSummary(
        locator="docx:para:1",
        object_type="paragraph",
        preview="Example",
        capabilities=(Capability.READ, Capability.UPDATE),
    )

    payload = ObjectPayload(
        document=document,
        locator="docx:document",
        object_type="document",
        preview="Preview",
        properties={"paragraph_count": 1},
        capabilities=(Capability.READ, Capability.ADD_CHILD),
        child_summary=(child,),
    )

    assert payload.parent_locator is None
    assert payload.child_summary == (child,)
    assert payload.metadata == {}


def test_mutation_and_batch_results_support_optional_output_path() -> None:
    result = MutationResult(
        document_path=Path("/tmp/example.docx"),
        output_path=None,
        document_id="doc-1",
        locator="docx:para:1",
        object_type="paragraph",
        summary="validated",
        capabilities=(Capability.READ, Capability.UPDATE),
    )
    batch = BatchResult(
        document_path=Path("/tmp/example.docx"),
        output_path=None,
        document_id="doc-1",
        summary="dry run",
        dry_run=True,
        operations=(result,),
    )

    assert batch.operations == (result,)
    assert batch.dry_run is True


def test_objects_package_exports_object_resolver_protocol() -> None:
    assert ObjectResolver.__name__ == "ObjectResolver"
