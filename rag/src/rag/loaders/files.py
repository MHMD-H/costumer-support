"""LangChain-backed loaders for unstructured local files."""

from __future__ import annotations

from pathlib import Path
from langchain_core.documents import Document

from rag.loaders.base import (
    MAX_DOCUMENT_BYTES, LoaderContext, SourceType, Visibility, enrich_documents,
)


class _FileLoader:
    source_type: SourceType

    def __init__(self, path: str | Path, *, tenant_id: str,
                 visibility: Visibility = "internal", title: str | None = None,
                 document_id: str | None = None) -> None:
        self.path = Path(path)
        self.context = LoaderContext(
            tenant_id=tenant_id, source_type=self.source_type,
            source=str(self.path), visibility=visibility, title=title,
            document_id=document_id,
        )

    def load(self) -> list[Document]:
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        size = self.path.stat().st_size
        if size > MAX_DOCUMENT_BYTES:
            raise ValueError(f"File too large: {self.path} exceeds the 100 MB limit")
        if size == 0:
            raise ValueError(f"Empty file: {self.path}")
        try:
            loader_type = self._loader_type()
        except ImportError as exc:
            raise RuntimeError("Install rag/requirements.txt to use file loaders") from exc
        documents = loader_type(str(self.path)).load()
        if not _has_content(documents):
            raise ValueError(f"Empty file: {self.path} contains no non-whitespace content")
        return enrich_documents(documents, self.context)

    def _loader_type(self) -> type:
        raise NotImplementedError


class PDFLoader(_FileLoader):
    source_type = "pdf"

    def _loader_type(self) -> type:
        from langchain_community.document_loaders.pdf import PyPDFLoader
        return PyPDFLoader


class TextFileLoader(_FileLoader):
    source_type = "txt"

    def _loader_type(self) -> type:
        from langchain_community.document_loaders.text import TextLoader
        return TextLoader


class MarkdownLoader(TextFileLoader):
    """Markdown file loader; heading-aware processing happens in the chunker."""

    source_type = "markdown"


class DocxLoader(_FileLoader):
    source_type = "docx"

    def _loader_type(self) -> type:
        from langchain_community.document_loaders.word_document import Docx2txtLoader
        return Docx2txtLoader


# Discoverable aliases matching the common file-extension names.
TXTLoader = TextFileLoader
DOCXLoader = DocxLoader


def _has_content(documents: list[Document]) -> bool:
    return any(document.page_content.strip() for document in documents)
