from __future__ import annotations

from datetime import datetime, timezone

from rag.core.contracts import DocumentChunkRecord
from rag.retrieval.metadata_filter import filter_chunks


def _chunk(
    chunk_id: str,
    *,
    tenant_id: str = "tenant-1",
    visibility: str = "internal",
) -> DocumentChunkRecord:
    return DocumentChunkRecord(
        id=chunk_id,
        document_id="doc-1",
        tenant_id=tenant_id,
        chunk_index=0,
        content="Returns policy",
        visibility=visibility,  # type: ignore[arg-type]
        chroma_collection="rag_documents",
        chroma_vector_id=f"doc-1:{chunk_id}",
        metadata={},
        created_at=datetime.now(timezone.utc),
    )


def test_document_chunk_record_matches_document_chunks_schema_fields() -> None:
    chunk = _chunk("chunk-1")

    assert chunk.id == "chunk-1"
    assert chunk.document_id == "doc-1"
    assert chunk.tenant_id == "tenant-1"
    assert chunk.chunk_index == 0
    assert chunk.content == "Returns policy"
    assert chunk.visibility == "internal"
    assert chunk.chroma_collection == "rag_documents"
    assert chunk.chroma_vector_id == "doc-1:chunk-1"
    assert chunk.metadata == {}
    assert chunk.created_at.tzinfo is not None


def test_default_visibility_allows_public_and_internal() -> None:
    chunks = [_chunk("internal"), _chunk("public", visibility="public")]

    assert [chunk.id for chunk in filter_chunks(chunks, tenant_id="tenant-1")] == [
        "internal", "public",
    ]


def test_public_only_visibility_filter() -> None:
    chunks = [_chunk("internal"), _chunk("public", visibility="public")]

    filtered = filter_chunks(chunks, tenant_id="tenant-1", allowed_visibility={"public"})

    assert [chunk.id for chunk in filtered] == ["public"]


def test_internal_only_visibility_filter() -> None:
    chunks = [_chunk("internal"), _chunk("public", visibility="public")]

    filtered = filter_chunks(chunks, tenant_id="tenant-1", allowed_visibility={"internal"})

    assert [chunk.id for chunk in filtered] == ["internal"]


def test_empty_visibility_set_returns_no_chunks() -> None:
    chunks = [_chunk("internal"), _chunk("public", visibility="public")]

    assert filter_chunks(chunks, tenant_id="tenant-1", allowed_visibility=set()) == []


def test_cross_tenant_chunks_are_filtered_out() -> None:
    chunks = [
        _chunk("own-public", visibility="public"),
        _chunk("other-public", tenant_id="tenant-2", visibility="public"),
    ]

    filtered = filter_chunks(chunks, tenant_id="tenant-1")

    assert [chunk.id for chunk in filtered] == ["own-public"]
