"""Web loading with layout/noise removal before chunking."""

from __future__ import annotations

import re
from collections.abc import Callable

from bs4 import BeautifulSoup
from langchain_core.documents import Document

from rag.loaders.base import LoaderContext, Visibility, enrich_documents

REMOVED_TAGS = ("script", "style", "noscript", "nav", "footer", "header", "aside", "form")


def clean_html(html: str) -> tuple[str, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    for node in soup.find_all(REMOVED_TAGS):
        node.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    lines = [re.sub(r"\s+", " ", line).strip() for line in root.get_text("\n").splitlines()]
    return "\n\n".join(line for line in lines if line), title


class WebPageLoader:
    def __init__(self, url: str, *, tenant_id: str,
                 visibility: Visibility = "internal", title: str | None = None,
                 document_id: str | None = None,
                 fetcher: Callable[[str], str] | None = None) -> None:
        self.url = url
        self.title = title
        self.fetcher = fetcher
        self.context = LoaderContext(
            tenant_id=tenant_id, source_type="web", source=url,
            visibility=visibility, title=title, document_id=document_id,
        )

    def load(self) -> list[Document]:
        if self.fetcher is not None:
            html = self.fetcher(self.url)
            loader_metadata = {"source": self.url}
        else:
            try:
                from langchain_community.document_loaders.web_base import WebBaseLoader
            except ImportError as exc:
                raise RuntimeError("Install rag/requirements.txt to load web pages") from exc
            web_loader = WebBaseLoader(self.url, raise_for_status=True)
            soup = web_loader.scrape()
            html = str(soup)
            loader_metadata = {"source": self.url}

        content, discovered_title = clean_html(html)
        loader_metadata["url"] = self.url
        if self.title is None and discovered_title:
            loader_metadata["title"] = discovered_title
        return enrich_documents(
            [Document(page_content=content, metadata=loader_metadata)], self.context
        )
