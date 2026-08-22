from __future__ import annotations

from zipfile import ZIP_DEFLATED, ZipFile

from langchain_core.documents import Document
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from pypdf import PdfWriter
import pytest

from rag.chunking import SourceAwareChunker
from rag.loaders import (
    CSVLoader, DocxLoader, MarkdownLoader, NotionMarkdownLoader, PDFLoader,
    TextFileLoader, WebPageLoader, create_loader, detect_source_type,
)
from rag.loaders.base import LoaderContext, enrich_documents


def test_pdf_loader_adds_page_and_persistence_metadata(tmp_path) -> None:
    path = tmp_path / "guide.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=100)
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }),
        }),
    })
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 50 Td (Return policy) Tj ET")
    page[NameObject("/Contents")] = stream
    with path.open("wb") as output:
        writer.write(output)

    documents = PDFLoader(path, tenant_id="tenant-1").load()

    assert len(documents) == 1
    assert documents[0].metadata["source_type"] == "pdf"
    assert documents[0].metadata["page"] == 0
    assert documents[0].metadata["document_id"]


def test_web_loader_removes_layout_noise_then_chunks() -> None:
    html = """
    <html><head><title>Returns</title><style>.x{}</style><script>bad()</script></head>
    <body><nav>Menu pricing login</nav><main><h1>Returns</h1>
    <p>Customers may return products within thirty days.</p></main><footer>Copyright</footer></body></html>
    """
    documents = WebPageLoader(
        "https://example.test/returns", tenant_id="tenant-1", fetcher=lambda _: html,
    ).load()
    chunks = SourceAwareChunker().split_documents(documents)

    assert documents[0].metadata["url"] == "https://example.test/returns"
    assert documents[0].metadata["title"] == "Returns"
    assert "Customers may return" in chunks[0].page_content
    assert all(noise not in chunks[0].page_content for noise in ("bad()", "Menu", "Copyright"))


def test_notion_loader_interface_requires_no_api_key_and_keeps_page_id() -> None:
    documents = NotionMarkdownLoader(
        "# Policies\n\n## Shipping\n\nShips next day.", notion_page_id="page-123",
        tenant_id="tenant-1", title="Policies",
    ).load()
    chunks = SourceAwareChunker().split_documents(documents)

    assert documents[0].metadata["notion_page_id"] == "page-123"
    assert any("Shipping" in chunk.metadata["section"] for chunk in chunks)


def test_inline_notion_without_stable_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="requires notion_page_id, source, or document_id"):
        NotionMarkdownLoader("# Policies", tenant_id="tenant-1")

    with pytest.raises(ValueError, match="requires notion_page_id, source, or document_id"):
        NotionMarkdownLoader("# Different Policies", tenant_id="tenant-1")


def test_csv_is_explicitly_deferred() -> None:
    try:
        CSVLoader("data.csv").load()
    except NotImplementedError as exc:
        assert "dataset semantics" in str(exc)
    else:
        raise AssertionError("CSV should remain deferred")


def test_local_source_types_are_inferred() -> None:
    assert detect_source_type("guide.pdf") == "pdf"
    assert detect_source_type("notes.txt") == "txt"
    assert detect_source_type("README.md") == "markdown"
    assert detect_source_type("README.markdown") == "markdown"
    assert detect_source_type("handbook.docx") == "docx"
    assert detect_source_type("records.csv") == "csv"


def test_factory_uses_langchain_file_loader_abstractions(tmp_path) -> None:
    text_path = tmp_path / "notes.txt"
    markdown_path = tmp_path / "notes.md"
    text_path.write_text("Plain text", encoding="utf-8")
    markdown_path.write_text("# Heading\n\nMarkdown text", encoding="utf-8")

    text_loader = create_loader(text_path, tenant_id="tenant-1")
    markdown_loader = create_loader(markdown_path, tenant_id="tenant-1")

    assert isinstance(text_loader, TextFileLoader)
    assert isinstance(markdown_loader, MarkdownLoader)
    assert text_loader.load()[0].page_content == "Plain text"
    assert markdown_loader.load()[0].metadata["source_type"] == "markdown"


def test_empty_text_file_fails_before_ingestion(tmp_path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Empty file"):
        TextFileLoader(path, tenant_id="tenant-1").load()


def test_whitespace_only_text_file_fails_after_loading(tmp_path) -> None:
    path = tmp_path / "blank.txt"
    path.write_text(" \n\t ", encoding="utf-8")

    with pytest.raises(ValueError, match="no non-whitespace content"):
        TextFileLoader(path, tenant_id="tenant-1").load()


def test_oversized_file_fails_before_ingestion(tmp_path) -> None:
    path = tmp_path / "huge.txt"
    with path.open("wb") as handle:
        handle.truncate(100 * 1024 * 1024 + 1)

    with pytest.raises(ValueError, match="100 MB limit"):
        TextFileLoader(path, tenant_id="tenant-1").load()


def test_docx_loads_through_langchain_abstraction(tmp_path) -> None:
    path = tmp_path / "policy.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body><w:p><w:r><w:t>Returns policy</w:t></w:r></w:p></w:body>
    </w:document>"""
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document_xml)

    documents = DocxLoader(path, tenant_id="tenant-1").load()

    assert documents[0].page_content == "Returns policy"
    assert documents[0].metadata["source_type"] == "docx"


def test_metadata_enricher_merges_loader_and_project_metadata() -> None:
    original = Document(page_content="Page", metadata={
        "source": "loader-source.pdf", "page": 4, "title": "Loader title",
        "producer": "Acme PDF",
    })
    context = LoaderContext(
        tenant_id="tenant-1", source_type="pdf", source="project-source.pdf",
    )

    enriched = enrich_documents([original], context)[0].metadata

    assert enriched["source"] == "loader-source.pdf"
    assert enriched["page"] == 4
    assert enriched["producer"] == "Acme PDF"
    assert enriched["title"] == "Loader title"
    assert enriched["visibility"] == "internal"
    assert enriched["created_at"] == enriched["updated_at"]


def test_notion_markdown_export_requires_explicit_type(tmp_path) -> None:
    path = tmp_path / "notion.md"
    path.write_text("# Handbook\n\n## Shipping\n\nShips tomorrow.", encoding="utf-8")

    loader = create_loader(
        path, tenant_id="tenant-1", source_type="notion", notion_page_id="page-1",
    )
    documents = loader.load()
    chunks = SourceAwareChunker().split_documents(documents)

    assert documents[0].metadata["source_type"] == "notion"
    assert documents[0].metadata["notion_page_id"] == "page-1"
    assert any("Shipping" in chunk.metadata["section"] for chunk in chunks)
