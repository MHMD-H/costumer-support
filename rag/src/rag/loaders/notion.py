"""Load Notion content supplied or exported as Markdown."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from rag.loaders.base import (
    MAX_DOCUMENT_BYTES, LoaderContext, Visibility, enrich_documents,
)


class NotionMarkdownLoader:
    """Load one Notion page without requiring credentials.

    Content may come from a Notion connector/API, or ``from_file`` may read a
    Markdown export. Heading-aware processing is performed by the chunker.
    """

    def __init__(self, markdown: str, *, tenant_id: str,
                 notion_page_id: str | None = None,
                 source: str | None = None, title: str | None = None,
                 visibility: Visibility = "internal",
                 document_id: str | None = None) -> None:
        if source is None and notion_page_id is None and document_id is None:
            raise ValueError(
                "Inline Notion content requires notion_page_id, source, or document_id"
            )
        self.markdown = markdown
        self.notion_page_id = notion_page_id
        self.path: Path | None = None
        self.context = LoaderContext(
            tenant_id=tenant_id, source_type="notion",
            source=source or (
                f"notion:{notion_page_id}" if notion_page_id else f"document:{document_id}"
            ),
            visibility=visibility,
            title=title, document_id=document_id,
        )

    @classmethod
    def from_file(cls, path: str | Path, *, tenant_id: str,
                  notion_page_id: str | None = None,
                  **kwargs: Any) -> "NotionMarkdownLoader":
        markdown_path = Path(path)
        loader = cls(
            "",
            notion_page_id=notion_page_id, tenant_id=tenant_id,
            source=str(markdown_path), **kwargs,
        )
        loader.path = markdown_path
        return loader

    def load(self) -> list[Document]:
        if self.path is None:
            documents = [Document(page_content=self.markdown)]
        else:
            size = self.path.stat().st_size
            if size > MAX_DOCUMENT_BYTES:
                raise ValueError(f"File too large: {self.path} exceeds the 100 MB limit")
            if size == 0:
                raise ValueError(f"Empty file: {self.path}")
            try:
                from langchain_community.document_loaders.text import TextLoader
            except ImportError as exc:
                raise RuntimeError("Install rag/requirements.txt to load Notion exports") from exc
            documents = TextLoader(str(self.path), encoding="utf-8").load()
        if not any(document.page_content.strip() for document in documents):
            source = self.path or self.context.source
            raise ValueError(f"Empty file: {source} contains no non-whitespace content")
        for document in documents:
            if self.notion_page_id:
                document.metadata["notion_page_id"] = self.notion_page_id
        return enrich_documents(documents, self.context)
