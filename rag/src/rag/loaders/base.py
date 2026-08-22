"""Shared metadata handling for ingestion loaders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document

SourceType = Literal["pdf", "txt", "markdown", "docx", "notion", "web", "csv"]
Visibility = Literal["public", "internal"]
MAX_DOCUMENT_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class LoaderContext:
    tenant_id: str
    source_type: SourceType
    source: str
    visibility: Visibility = "internal"
    title: str | None = None
    document_id: str | None = None

    def metadata(self, *, _ingested_at: str | None = None, **loader_metadata: Any) -> dict[str, Any]:
        """Merge LangChain metadata with the project's ingestion metadata."""
        metadata = {key: value for key, value in loader_metadata.items() if value is not None}
        source = metadata.get("source") or self.source
        canonical_source = _canonical_source(self.source_type, str(source))
        document_id = self.document_id or str(
            uuid5(NAMESPACE_URL, f"{self.tenant_id}:{self.source_type}:{canonical_source}")
        )
        timestamp = _ingested_at or datetime.now(timezone.utc).isoformat()
        metadata.update({
            "tenant_id": self.tenant_id,
            "source_type": self.source_type,
            "source": source,
            "canonical_source": canonical_source,
            "title": self.title or metadata.get("title") or _default_title(str(source)),
            "visibility": self.visibility,
            "document_id": document_id,
            # PostgreSQL will become the source of truth for these timestamps
            # when database integration is added.
            "created_at": timestamp,
            "updated_at": timestamp,
        })
        return metadata


def enrich_documents(documents: list[Document], context: LoaderContext) -> list[Document]:
    ingested_at = datetime.now(timezone.utc).isoformat()
    for document in documents:
        document.metadata = context.metadata(_ingested_at=ingested_at, **document.metadata)
    return documents


def _default_title(source: str) -> str:
    path_name = Path(source).name
    return Path(path_name).stem or source


def _canonical_source(source_type: SourceType, source: str) -> str:
    if source_type in {"pdf", "txt", "markdown", "docx", "csv"}:
        return str(Path(source).expanduser().resolve())
    if source_type == "web":
        return source.strip().lower()
    return source.strip()
