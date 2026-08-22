"""Standalone load -> clean/format -> chunk -> embed -> Chroma workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from langchain_core.documents import Document

from rag.chunking import SourceAwareChunker
from rag.core.config import RagSettings
from rag.embeddings import EmbeddingConfig, create_embeddings
from rag.loaders import create_loader
from rag.loaders.base import SourceType
from rag.vectorstores import ChromaStore


class DocumentLoader(Protocol):
    def load(self) -> list[Document]: ...


@dataclass(frozen=True)
class IngestionResult:
    document_ids: list[str]
    document_metadata: list[dict[str, Any]]
    chunks: list[Document]
    vector_ids: list[str]


class IngestionPipeline:
    def __init__(self, *, chunker: SourceAwareChunker, store: ChromaStore) -> None:
        self.chunker = chunker
        self.store = store
        self._known_document_identities: set[tuple[str, str, str]] = set()

    @classmethod
    def from_settings(cls, settings: RagSettings | None = None) -> "IngestionPipeline":
        """Build the default Hugging Face -> Chroma ingestion pipeline."""
        selected = settings or RagSettings()
        embeddings = create_embeddings(EmbeddingConfig(
            model_name=selected.embedding_model,
            device=selected.embedding_device,
        ))
        return cls(
            chunker=SourceAwareChunker(selected),
            store=ChromaStore(
                embeddings,
                collection_name=selected.chroma_collection_name,
                persist_directory=selected.chroma_persist_directory,
            ),
        )

    def ingest(self, loader: DocumentLoader, *, replace: bool = False) -> IngestionResult:
        documents = self._load_documents(loader)
        self._validate_documents_not_empty(documents)
        identities = self._document_identities(documents)
        self._check_duplicate_identities(identities, replace=replace)
        chunks = self._split_documents(documents)
        document_metadata = self._document_metadata(documents)
        document_ids = [metadata["document_id"] for metadata in document_metadata]
        del documents

        # TODO: Persist document and chunk metadata later from the FastAPI document service after the RAG pipeline is verified.
        if replace and not chunks:
            raise ValueError(
                "Replacement produced no chunks; existing Chroma vectors were not deleted"
            )
        if not chunks:
            vector_ids: list[str] = []
        elif replace:
            vector_ids = []
            for document_id in document_ids:
                document_chunks = [
                    chunk for chunk in chunks
                    if chunk.metadata.get("document_id") == document_id
                ]
                tenant_id = str(document_chunks[0].metadata["tenant_id"])
                vector_ids.extend(self.store.replace_document(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    documents=document_chunks,
                ))
        else:
            vector_ids = self.store.add_documents(chunks)
        self._known_document_identities.update(identities)
        return IngestionResult(
            document_ids=document_ids,
            document_metadata=document_metadata,
            chunks=chunks,
            vector_ids=vector_ids,
        )

    def ingest_source(
        self,
        source: str | Path,
        *,
        tenant_id: str,
        source_type: SourceType | None = None,
        replace: bool = False,
        **loader_options: Any,
    ) -> IngestionResult:
        """Infer ordinary files and ingest explicit web/Notion sources."""
        loader = create_loader(
            source,
            tenant_id=tenant_id,
            source_type=source_type,
            **loader_options,
        )
        return self.ingest(loader, replace=replace)  # type: ignore[arg-type]

    def _load_documents(self, loader: DocumentLoader) -> list[Document]:
        try:
            return loader.load()
        except Exception as exc:
            raise type(exc)(f"load failed for {loader.__class__.__name__}: {exc}") from exc

    @staticmethod
    def _validate_documents_not_empty(documents: list[Document]) -> None:
        if not documents or not any(document.page_content.strip() for document in documents):
            raise ValueError("empty document: loaded content contains no non-whitespace text")

    def _split_documents(self, documents: list[Document]) -> list[Document]:
        try:
            return self.chunker.split_documents(documents)
        except Exception as exc:
            source = _first_metadata_value(documents, "source") or "unknown source"
            raise RuntimeError(f"chunking failed for {source}: {exc}") from exc

    def _check_duplicate_identities(
        self,
        identities: set[tuple[str, str, str]],
        *,
        replace: bool,
    ) -> None:
        if replace:
            return
        duplicates = identities & self._known_document_identities
        for tenant_id, source_type, canonical_source in identities:
            if self.store.has_document_identity(
                tenant_id=tenant_id,
                source_type=source_type,
                canonical_source=canonical_source,
            ):
                duplicates.add((tenant_id, source_type, canonical_source))
        if duplicates:
            duplicate = sorted(duplicates)[0]
            raise ValueError(
                "Duplicate document identity; pass replace=True to replace existing chunks "
                f"(tenant_id={duplicate[0]}, source_type={duplicate[1]}, source={duplicate[2]})"
            )

    @staticmethod
    def _document_identities(documents: list[Document]) -> set[tuple[str, str, str]]:
        identities: set[tuple[str, str, str]] = set()
        for document in documents:
            metadata = document.metadata
            identities.add((
                str(metadata["tenant_id"]),
                str(metadata["source_type"]),
                str(metadata["canonical_source"]),
            ))
        return identities

    @staticmethod
    def _document_metadata(documents: list[Document]) -> list[dict[str, Any]]:
        metadata_by_id: dict[str, dict[str, Any]] = {}
        for document in documents:
            metadata = dict(document.metadata)
            metadata_by_id.setdefault(str(metadata["document_id"]), metadata)
        return list(metadata_by_id.values())


def _first_metadata_value(documents: list[Document], key: str) -> Any:
    for document in documents:
        if key in document.metadata:
            return document.metadata[key]
    return None
