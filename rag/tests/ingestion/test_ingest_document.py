from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
import pytest

from rag.chunking import SourceAwareChunker
from rag.core.config import RagSettings
from rag.ingestion import IngestionPipeline
from rag.loaders import WebPageLoader
from rag.vectorstores.chroma import ChromaStore, normalize_chroma_metadata


class DeterministicEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(text.count("return")), 1.0] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class EmptyChunker:
    def split_documents(self, documents: list[Document]) -> list[Document]:
        return []


def test_pipeline_embeds_and_persists_to_chroma(tmp_path) -> None:
    loader = WebPageLoader(
        "https://example.test/returns", tenant_id="tenant-1", visibility="public",
        fetcher=lambda _: "<main><h1>Returns</h1><p>Return items in 30 days.</p></main>",
    )
    store = ChromaStore(
        DeterministicEmbeddings(), collection_name="test_collection",
        persist_directory=tmp_path / "chroma",
    )
    result = IngestionPipeline(chunker=SourceAwareChunker(), store=store).ingest(loader)

    assert len(result.document_ids) == 1
    assert result.vector_ids == [result.chunks[0].metadata["chroma_vector_id"]]
    stored = store.vectorstore.get(ids=result.vector_ids)
    assert stored["metadatas"][0]["tenant_id"] == "tenant-1"
    assert stored["metadatas"][0]["visibility"] == "public"
    assert stored["metadatas"][0]["chunk_id"] != result.vector_ids[0]
    assert stored["metadatas"][0]["chroma_vector_id"] == result.vector_ids[0]
    assert stored["metadatas"][0]["chroma_collection"] == "test_collection"


def test_reingesting_smaller_document_replaces_stale_chroma_chunks(tmp_path) -> None:
    store = ChromaStore(
        DeterministicEmbeddings(), collection_name="replace_collection",
        persist_directory=tmp_path / "chroma",
    )
    pipeline = IngestionPipeline(
        chunker=SourceAwareChunker(RagSettings(chunk_size=40, chunk_overlap=0)),
        store=store,
    )

    first = pipeline.ingest(WebPageLoader(
        "https://example.test/policy", tenant_id="tenant-1",
        fetcher=lambda _: "<main><p>Returns allowed. " * 10 + "</p></main>",
    ))
    second = pipeline.ingest(WebPageLoader(
        "https://example.test/policy", tenant_id="tenant-1",
        fetcher=lambda _: "<main><p>Returns allowed.</p></main>",
    ), replace=True)

    assert len(first.vector_ids) > len(second.vector_ids)
    stored = store.vectorstore.get(where={"$and": [
        {"tenant_id": {"$eq": "tenant-1"}},
        {"document_id": {"$eq": second.document_ids[0]}},
    ]})
    assert sorted(stored["ids"]) == sorted(second.vector_ids)


def test_empty_replacement_batch_fails_without_deleting_existing_vectors(tmp_path) -> None:
    store = ChromaStore(
        DeterministicEmbeddings(), collection_name="empty_replace_collection",
        persist_directory=tmp_path / "chroma",
    )
    loader = WebPageLoader(
        "https://example.test/policy", tenant_id="tenant-1",
        fetcher=lambda _: "<main><p>Returns allowed.</p></main>",
    )
    original = IngestionPipeline(chunker=SourceAwareChunker(), store=store).ingest(loader)

    with pytest.raises(ValueError, match="Replacement produced no chunks"):
        IngestionPipeline(chunker=EmptyChunker(), store=store).ingest(loader, replace=True)  # type: ignore[arg-type]

    stored = store.vectorstore.get(where={"$and": [
        {"tenant_id": {"$eq": "tenant-1"}},
        {"document_id": {"$eq": original.document_ids[0]}},
    ]})
    assert sorted(stored["ids"]) == sorted(original.vector_ids)


def test_duplicate_document_requires_explicit_replace(tmp_path) -> None:
    store = ChromaStore(
        DeterministicEmbeddings(), collection_name="duplicate_collection",
        persist_directory=tmp_path / "chroma",
    )
    pipeline = IngestionPipeline(chunker=SourceAwareChunker(), store=store)
    loader = WebPageLoader(
        "https://example.test/policy", tenant_id="tenant-1",
        fetcher=lambda _: "<main><p>Returns allowed.</p></main>",
    )

    pipeline.ingest(loader)

    with pytest.raises(ValueError, match="Duplicate document identity"):
        pipeline.ingest(loader)


def test_duplicate_chunk_ids_raise_before_chroma_mutation(tmp_path) -> None:
    store = ChromaStore(
        DeterministicEmbeddings(), collection_name="duplicate_chunk_collection",
        persist_directory=tmp_path / "chroma",
    )
    documents = [
        Document(page_content="First", metadata={
            "chunk_id": "duplicate", "chroma_vector_id": "doc-1:0",
            "tenant_id": "tenant-1", "document_id": "doc-1",
        }),
        Document(page_content="Second", metadata={
            "chunk_id": "duplicate", "chroma_vector_id": "doc-1:1",
            "tenant_id": "tenant-1", "document_id": "doc-1",
        }),
    ]

    with pytest.raises(ValueError, match="Chunk record IDs must be unique"):
        store.add_documents(documents)

    assert store.vectorstore.get()["ids"] == []


def test_duplicate_chroma_vector_ids_raise_before_chroma_mutation(tmp_path) -> None:
    store = ChromaStore(
        DeterministicEmbeddings(), collection_name="duplicate_vector_collection",
        persist_directory=tmp_path / "chroma",
    )
    documents = [
        Document(page_content="First", metadata={
            "chunk_id": "1c903b31-c070-5b1e-8672-152f7e08fd7d",
            "chroma_vector_id": "duplicate",
            "tenant_id": "tenant-1",
            "document_id": "doc-1",
        }),
        Document(page_content="Second", metadata={
            "chunk_id": "908bc88c-b628-5bf8-a0db-9ff8256747c3",
            "chroma_vector_id": "duplicate",
            "tenant_id": "tenant-1",
            "document_id": "doc-1",
        }),
    ]

    with pytest.raises(ValueError, match="Chroma vector IDs must be unique"):
        store.add_documents(documents)

    assert store.vectorstore.get()["ids"] == []


def test_chroma_metadata_is_normalized_to_safe_scalars() -> None:
    normalized = normalize_chroma_metadata({
        "plain": "value",
        "count": 3,
        "enabled": True,
        "nothing": None,
        "created": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "nested": {"tags": ["returns", "shipping"]},
    })

    assert normalized["plain"] == "value"
    assert normalized["count"] == 3
    assert normalized["enabled"] is True
    assert "nothing" not in normalized
    assert normalized["created"].startswith("2026-01-02T00:00:00")
    assert normalized["nested"] == '{"tags": ["returns", "shipping"]}'
