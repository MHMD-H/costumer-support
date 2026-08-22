"""Source-aware LangChain document chunking."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from rag.core.config import RagSettings


class SourceAwareChunker:
    def __init__(self, settings: RagSettings | None = None) -> None:
        self.settings = settings or RagSettings()
        self.recursive = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
        )

    def split_documents(self, documents: list[Document]) -> list[Document]:
        chunks: list[Document] = []
        next_index_by_document: dict[str, int] = {}
        for document in documents:
            source_type = document.metadata.get("source_type")
            if source_type == "csv":
                raise NotImplementedError("CSV requires a dataset-specific chunking strategy")
            source_chunks = (
                self._split_markdown(document)
                if source_type in {"notion", "markdown"}
                else self.recursive.split_documents([document])
            )
            document_id = str(document.metadata["document_id"])
            next_index = next_index_by_document.get(document_id, 0)
            for offset, chunk in enumerate(source_chunks):
                index = next_index + offset
                chunk_record_id = str(uuid5(NAMESPACE_URL, f"{document_id}:{index}"))
                chunk.metadata["chunk_index"] = index
                chunk.metadata["document_id"] = document_id
                chunk.metadata["chunk_id"] = chunk_record_id
                chunk.metadata["id"] = chunk_record_id
                chunk.metadata["chroma_vector_id"] = f"{document_id}:{index}"
                chunks.append(chunk)
            next_index_by_document[document_id] = next_index + len(source_chunks)
        return chunks

    def _split_markdown(self, document: Document) -> list[Document]:
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "heading_1"), ("##", "heading_2"),
                                 ("###", "heading_3"), ("####", "heading_4")],
            strip_headers=False,
        )
        sections = header_splitter.split_text(document.page_content)
        for section in sections:
            headings = [
                section.metadata[key]
                for key in ("heading_1", "heading_2", "heading_3", "heading_4")
                if section.metadata.get(key)
            ]
            section.metadata = {
                **document.metadata,
                **section.metadata,
                "section": " > ".join(headings) if headings else "root",
            }
        return self.recursive.split_documents(sections)
