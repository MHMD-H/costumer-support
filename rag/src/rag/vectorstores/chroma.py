"""Chroma persistence adapter for LangChain documents."""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class ChromaStore:
    def __init__(self, embeddings: Embeddings, *, collection_name: str = "rag_documents",
                 persist_directory: str | Path = ".chroma") -> None:
        try:
            from langchain_chroma import Chroma
        except ImportError as exc:
            raise RuntimeError("Install rag/requirements.txt to use Chroma") from exc
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.vectorstore: Any = Chroma(
            collection_name=collection_name,
            persist_directory=str(self.persist_directory),
            embedding_function=embeddings,
            collection_metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, documents: list[Document]) -> list[str]:
        prepared = self._prepare_documents(documents)
        ids = _validate_batch_ids(prepared)
        return self.vectorstore.add_documents(documents=prepared, ids=ids)

    def replace_document(self, *, tenant_id: str, document_id: str,
                         documents: list[Document]) -> list[str]:
        prepared = self._prepare_documents(documents)
        if not prepared:
            raise ValueError(
                "Replacement batch produced no chunks; existing Chroma vectors were not deleted"
            )
        ids = _validate_batch_ids(prepared)
        for document in prepared:
            metadata = document.metadata
            if metadata.get("tenant_id") != tenant_id or metadata.get("document_id") != document_id:
                raise ValueError(
                    "Replacement batch must contain only chunks for the requested tenant_id and document_id"
                )

        self.vectorstore.delete(where={"$and": [
            {"tenant_id": {"$eq": tenant_id}},
            {"document_id": {"$eq": document_id}},
        ]})
        return self.vectorstore.add_documents(documents=prepared, ids=ids)

    def has_document_identity(self, *, tenant_id: str, source_type: str,
                              canonical_source: str) -> bool:
        result = self.vectorstore.get(
            where={"$and": [
                {"tenant_id": {"$eq": tenant_id}},
                {"source_type": {"$eq": source_type}},
                {"canonical_source": {"$eq": canonical_source}},
            ]},
            limit=1,
        )
        return bool(result.get("ids"))

    def _prepare_documents(self, documents: list[Document]) -> list[Document]:
        prepared: list[Document] = []
        for document in documents:
            metadata = dict(document.metadata)
            if "chunk_id" not in metadata:
                raise ValueError("Chunk metadata must include chunk_id before Chroma ingestion")
            if "chroma_vector_id" not in metadata:
                raise ValueError("Chunk metadata must include chroma_vector_id before Chroma ingestion")
            metadata["chroma_collection"] = metadata.get("chroma_collection") or self.collection_name
            prepared.append(Document(
                page_content=document.page_content,
                metadata=normalize_chroma_metadata(metadata),
            ))
        return prepared


def normalize_chroma_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Return metadata values that Chroma accepts reliably."""
    normalized: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            normalized[key] = value
        elif isinstance(value, (datetime, date)):
            normalized[key] = value.isoformat()
        else:
            try:
                normalized[key] = json.dumps(value, sort_keys=True, default=str)
            except TypeError:
                normalized[key] = str(value)
    return normalized


def _validate_batch_ids(documents: list[Document]) -> list[str]:
    chunk_ids = [str(document.metadata["chunk_id"]) for document in documents]
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("Chunk record IDs must be unique within an ingestion batch")
    vector_ids = [str(document.metadata["chroma_vector_id"]) for document in documents]
    if len(vector_ids) != len(set(vector_ids)):
        raise ValueError("Chroma vector IDs must be unique within an ingestion batch")
    return vector_ids
