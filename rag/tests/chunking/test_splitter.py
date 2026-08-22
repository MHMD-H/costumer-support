from uuid import UUID

from langchain_core.documents import Document

from rag.chunking import SourceAwareChunker
from rag.core.config import RagSettings


def test_recursive_chunking_preserves_filter_metadata() -> None:
    document = Document(
        page_content="First paragraph. " * 30,
        metadata={
            "tenant_id": "tenant-1", "source_type": "txt", "source": "a.txt",
            "title": "A", "visibility": "internal", "document_id": "doc-1",
        },
    )
    chunks = SourceAwareChunker(RagSettings(chunk_size=100, chunk_overlap=10)).split_documents([document])

    assert len(chunks) > 1
    assert [chunk.metadata["chunk_index"] for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.metadata["tenant_id"] == "tenant-1" for chunk in chunks)
    assert all(chunk.metadata["visibility"] == "internal" for chunk in chunks)


def test_notion_markdown_preserves_heading_as_section() -> None:
    document = Document(
        page_content="# Handbook\n\n## Returns\n\nReturns are accepted within 30 days.",
        metadata={
            "tenant_id": "tenant-1", "source_type": "notion", "source": "notion:1",
            "title": "Handbook", "visibility": "internal", "document_id": "doc-1",
            "notion_page_id": "1",
        },
    )
    chunks = SourceAwareChunker().split_documents([document])

    assert chunks
    assert any("Handbook" in chunk.metadata["section"] for chunk in chunks)
    assert any("Returns" in chunk.metadata["section"] for chunk in chunks)


def test_chunk_indices_remain_unique_across_pdf_pages() -> None:
    metadata = {
        "tenant_id": "tenant-1", "source_type": "pdf", "source": "guide.pdf",
        "title": "Guide", "visibility": "internal", "document_id": "doc-1",
    }
    pages = [
        Document(page_content="Page one content.", metadata={**metadata, "page": 0}),
        Document(page_content="Page two content.", metadata={**metadata, "page": 1}),
    ]
    chunks = SourceAwareChunker().split_documents(pages)

    assert [chunk.metadata["chunk_index"] for chunk in chunks] == [0, 1]
    assert [chunk.metadata["chroma_vector_id"] for chunk in chunks] == ["doc-1:0", "doc-1:1"]
    assert [UUID(chunk.metadata["chunk_id"]) for chunk in chunks]
    assert chunks[0].metadata["chunk_id"] != chunks[0].metadata["chroma_vector_id"]
    assert chunks[0].metadata["id"] == chunks[0].metadata["chunk_id"]
