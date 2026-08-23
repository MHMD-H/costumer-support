"""Core contracts shared across the RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

Visibility = Literal["public", "internal"]
SourceType = Literal["pdf", "txt", "markdown", "docx", "notion", "web", "csv"]


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    tenant_id: str
    title: str
    source_type: SourceType
    source: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    visibility: Visibility = "internal"


@dataclass(frozen=True)
class DocumentChunkRecord:
    id: str
    document_id: str
    tenant_id: str
    chunk_index: int
    content: str
    visibility: Visibility
    chroma_collection: str
    chroma_vector_id: str
    metadata: dict[str, Any]
    created_at: datetime


# Short name retained for search-facing type annotations; the canonical project
# contract is DocumentChunkRecord and uses database terminology.
Chunk = DocumentChunkRecord


@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float
    keyword_score: float = 0.0
    semantic_score: float = 0.0


@dataclass(frozen=True)
class AnswerSource:
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    sources: list[AnswerSource]
