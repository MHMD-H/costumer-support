"""RAG configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RagSettings:
    chunk_size: int = 800
    chunk_overlap: int = 120
    default_top_k: int = 5
    hybrid_keyword_weight: float = 0.45
    hybrid_semantic_weight: float = 0.55
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "cpu"
    chroma_collection_name: str = "rag_documents"
    chroma_persist_directory: str = ".chroma"

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.default_top_k <= 0:
            raise ValueError("default_top_k must be positive")
        if not self.embedding_model.strip():
            raise ValueError("embedding_model cannot be empty")
        if not self.chroma_collection_name.strip():
            raise ValueError("chroma_collection_name cannot be empty")

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_persist_directory)
