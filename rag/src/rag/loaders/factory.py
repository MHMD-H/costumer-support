"""Source inference and loader construction for standalone ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rag.loaders.base import SourceType
from rag.loaders.csv import CSVLoader
from rag.loaders.files import DocxLoader, MarkdownLoader, PDFLoader, TextFileLoader
from rag.loaders.notion import NotionMarkdownLoader
from rag.loaders.web import WebPageLoader

_EXTENSION_TYPES: dict[str, SourceType] = {
    ".pdf": "pdf",
    ".txt": "txt",
    ".md": "markdown",
    ".markdown": "markdown",
    ".docx": "docx",
    ".csv": "csv",
}


def detect_source_type(path: str | Path) -> SourceType:
    """Infer the supported local source type from a file extension."""
    suffix = Path(path).suffix.lower()
    try:
        return _EXTENSION_TYPES[suffix]
    except KeyError as exc:
        raise ValueError(
            f"Cannot infer source type from {path!s}; pass source_type explicitly"
        ) from exc


def create_loader(
    source: str | Path,
    *,
    tenant_id: str,
    source_type: SourceType | None = None,
    **kwargs: Any,
) -> object:
    """Create the single supported loader for a local file, web page, or Notion export."""
    selected = source_type or detect_source_type(source)
    if selected == "web":
        return WebPageLoader(str(source), tenant_id=tenant_id, **kwargs)
    if selected == "notion":
        path = Path(source)
        if not path.is_file():
            raise ValueError("Notion input must be a local Markdown export path")
        return NotionMarkdownLoader.from_file(path, tenant_id=tenant_id, **kwargs)

    loaders = {
        "pdf": PDFLoader,
        "txt": TextFileLoader,
        "markdown": MarkdownLoader,
        "docx": DocxLoader,
        "csv": CSVLoader,
    }
    try:
        loader_type = loaders[selected]
    except KeyError as exc:
        raise ValueError(f"Unsupported source type: {selected}") from exc
    return loader_type(source, tenant_id=tenant_id, **kwargs)
