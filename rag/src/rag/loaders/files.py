"""LangChain-backed loaders for unstructured local files."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from langchain_core.documents import Document

from rag.loaders.base import (
    MAX_DOCUMENT_BYTES, LoaderContext, SourceType, Visibility, enrich_documents,
)


class _FileLoader:
    source_type: SourceType

    def __init__(self, path: str | Path, *, tenant_id: str,
                 visibility: Visibility = "internal", title: str | None = None,
                 document_id: str | None = None, source_name: str | None = None,
                 max_bytes: int = MAX_DOCUMENT_BYTES) -> None:
        self.path = Path(path)
        self.source_name = source_name
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self.max_bytes = min(max_bytes, MAX_DOCUMENT_BYTES)
        self.context = LoaderContext(
            tenant_id=tenant_id, source_type=self.source_type,
            source=source_name or str(self.path), visibility=visibility, title=title,
            document_id=document_id,
            canonical_source=f"upload:{document_id}" if source_name and document_id else None,
        )

    def load(self) -> list[Document]:
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        size = self.path.stat().st_size
        if size > self.max_bytes:
            limit_label = "100 MB limit" if self.max_bytes == MAX_DOCUMENT_BYTES else "configured limit"
            raise ValueError(f"File too large: {self.path} exceeds the {limit_label}")
        if size == 0:
            raise ValueError(f"Empty file: {self.path}")
        try:
            loader_type = self._loader_type()
        except ImportError as exc:
            raise RuntimeError("Install rag/requirements.txt to use file loaders") from exc
        documents = loader_type(str(self.path)).load()
        if not _has_content(documents):
            raise ValueError(f"Empty file: {self.path} contains no non-whitespace content")
        if self.source_name:
            for document in documents:
                document.metadata["source"] = self.source_name
        return enrich_documents(documents, self.context)

    def _loader_type(self):
        raise NotImplementedError


class PDFLoader(_FileLoader):
    source_type = "pdf"

    def _loader_type(self):
        from langchain_community.document_loaders.pdf import PyPDFLoader
        return PyPDFLoader


class TextFileLoader(_FileLoader):
    source_type = "txt"

    def _loader_type(self):
        from langchain_community.document_loaders.text import TextLoader
        return partial(TextLoader, encoding="utf-8-sig")


class MarkdownLoader(TextFileLoader):
    """Markdown file loader; heading-aware processing happens in the chunker."""

    source_type = "markdown"


class DocxLoader(_FileLoader):
    source_type = "docx"

    def _loader_type(self):
        from langchain_community.document_loaders.word_document import Docx2txtLoader
        return Docx2txtLoader


# Discoverable aliases matching the common file-extension names.
TXTLoader = TextFileLoader
DOCXLoader = DocxLoader


def _has_content(documents: list[Document]) -> bool:
    return any(document.page_content.strip() for document in documents)
