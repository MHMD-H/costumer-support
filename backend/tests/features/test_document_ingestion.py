"""Task 21: stored uploads reach the existing LangChain ingestion pipeline."""

import asyncio
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

import pytest
from fastapi import HTTPException
from langchain_core.embeddings import Embeddings
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.db.models import Document
from app.features import documents as service
from app.features.document_uploads import save_upload
from rag.chunking import SourceAwareChunker
from rag.core.config import RagSettings
from rag.ingestion import IngestionPipeline
from rag.vectorstores import ChromaStore


class DeterministicEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(text.count("policy")), 1.0] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def make_pipeline(tmp_path):
    store = ChromaStore(
        DeterministicEmbeddings(), collection_name="task21",
        persist_directory=tmp_path / "chroma",
    )
    return IngestionPipeline(
        chunker=SourceAwareChunker(RagSettings(chunk_size=80, chunk_overlap=10)),
        store=store,
    )


def pdf_bytes(text: str | None) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    if text:
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
        })
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def docx_bytes(text: str) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>",
        )
    return output.getvalue()


def make_document(tenant_id, document_id, extension, visibility="internal"):
    now = datetime.now(timezone.utc)
    return Document(
        id=document_id, tenant_id=tenant_id, uploaded_by_user_id=uuid4(),
        title="Refund Policy", type=extension, source=f"policy.{extension}",
        visibility=visibility, status="uploaded", metadata_={},
        created_at=now, updated_at=now,
    )


@pytest.mark.parametrize("extension,content", [
    ("txt", "# Refund Policy\r\nCafe\u0301 items can be returned in 30 days.\n".encode("utf-8")),
    ("pdf", pdf_bytes("Refund Policy: 30 days")),
    ("docx", docx_bytes("Refund Policy: 30 days")),
])
def test_stored_file_indexes_with_postgres_identity_and_safe_metadata(
    tmp_path, monkeypatch, extension, content
):
    tenant_id, document_id = uuid4(), uuid4()
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    save_upload(tenant_id, document_id, extension, content)
    document = make_document(tenant_id, document_id, extension, visibility="public")
    queries = []

    async def get_document(_session, requested_tenant, requested_document):
        queries.append((requested_tenant, requested_document))
        return document if (requested_tenant, requested_document) == (tenant_id, document_id) else None

    monkeypatch.setattr(service.document_repository, "get_document_by_id", get_document)
    pipeline = make_pipeline(tmp_path)
    result = asyncio.run(service.ingest_uploaded_document(None, tenant_id, document_id, pipeline=pipeline))

    assert queries == [(tenant_id, document_id)]
    assert result.document_ids == [str(document_id)]
    assert result.chunks and len(result.vector_ids) == len(result.chunks)
    assert all(chunk.metadata["document_id"] == str(document_id) for chunk in result.chunks)
    assert all(chunk.metadata["tenant_id"] == str(tenant_id) for chunk in result.chunks)
    assert all(chunk.metadata["visibility"] == "public" for chunk in result.chunks)
    assert all(chunk.metadata["source"] == f"policy.{extension}" for chunk in result.chunks)
    assert all(chunk.metadata["canonical_source"] == f"upload:{document_id}" for chunk in result.chunks)
    assert all(chunk.metadata["chunk_id"] for chunk in result.chunks)
    if extension == "pdf":
        assert result.chunks[0].metadata["page"] == 0
    if extension == "txt":
        assert "# Refund Policy" in result.chunks[0].page_content
        assert "Café" in result.chunks[0].page_content
    stored = pipeline.store.vectorstore.get(ids=result.vector_ids)
    assert all(metadata["document_id"] == str(document_id) for metadata in stored["metadatas"])
    assert all(metadata["source"] == f"policy.{extension}" for metadata in stored["metadatas"])


def test_empty_extraction_leaves_chroma_empty(tmp_path, monkeypatch):
    tenant_id, document_id = uuid4(), uuid4()
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    save_upload(tenant_id, document_id, "pdf", pdf_bytes(None))
    document = make_document(tenant_id, document_id, "pdf")

    async def get_document(_session, _tenant, _document):
        return document

    monkeypatch.setattr(service.document_repository, "get_document_by_id", get_document)
    pipeline = make_pipeline(tmp_path)
    with pytest.raises(ValueError, match="Empty file|empty document"):
        asyncio.run(service.ingest_uploaded_document(None, tenant_id, document_id, pipeline=pipeline))
    assert pipeline.store.vectorstore.get()["ids"] == []


def test_missing_stored_file_fails_without_vectors(tmp_path, monkeypatch):
    tenant_id, document_id = uuid4(), uuid4()
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    document = make_document(tenant_id, document_id, "txt")

    async def get_document(_session, _tenant, _document):
        return document

    monkeypatch.setattr(service.document_repository, "get_document_by_id", get_document)
    pipeline = make_pipeline(tmp_path)
    with pytest.raises(FileNotFoundError):
        asyncio.run(service.ingest_uploaded_document(None, tenant_id, document_id, pipeline=pipeline))
    assert pipeline.store.vectorstore.get()["ids"] == []


def test_cross_tenant_document_is_404_before_vector_access(tmp_path, monkeypatch):
    tenant_id, other_tenant_id, document_id = uuid4(), uuid4(), uuid4()
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    save_upload(other_tenant_id, document_id, "txt", b"Private policy")

    async def get_document(_session, requested_tenant, _document):
        return None if requested_tenant == tenant_id else make_document(other_tenant_id, document_id, "txt")

    monkeypatch.setattr(service.document_repository, "get_document_by_id", get_document)
    pipeline = make_pipeline(tmp_path)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.ingest_uploaded_document(None, tenant_id, document_id, pipeline=pipeline))
    assert exc.value.status_code == 404
    assert pipeline.store.vectorstore.get()["ids"] == []


@pytest.mark.parametrize("extension,content", [
    ("txt", b"  \n\t  "),
    ("docx", b"PK\x03\x04broken archive"),
])
def test_unusable_stored_content_never_reaches_chroma(tmp_path, monkeypatch, extension, content):
    tenant_id, document_id = uuid4(), uuid4()
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    save_upload(tenant_id, document_id, extension, content)
    document = make_document(tenant_id, document_id, extension)

    async def get_document(_session, _tenant, _document):
        return document

    monkeypatch.setattr(service.document_repository, "get_document_by_id", get_document)
    pipeline = make_pipeline(tmp_path)
    with pytest.raises((ValueError, BadZipFile)):
        asyncio.run(service.ingest_uploaded_document(None, tenant_id, document_id, pipeline=pipeline))
    assert pipeline.store.vectorstore.get()["ids"] == []


def test_same_filename_in_two_tenants_remains_separate(tmp_path, monkeypatch):
    tenant_a, tenant_b = uuid4(), uuid4()
    document_a, document_b = uuid4(), uuid4()
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    save_upload(tenant_a, document_a, "txt", b"Tenant A policy")
    save_upload(tenant_b, document_b, "txt", b"Tenant B policy")
    documents = {
        (tenant_a, document_a): make_document(tenant_a, document_a, "txt"),
        (tenant_b, document_b): make_document(tenant_b, document_b, "txt"),
    }

    async def get_document(_session, tenant_id, document_id):
        return documents.get((tenant_id, document_id))

    monkeypatch.setattr(service.document_repository, "get_document_by_id", get_document)
    pipeline = make_pipeline(tmp_path)
    result_a = asyncio.run(service.ingest_uploaded_document(None, tenant_a, document_a, pipeline=pipeline))
    result_b = asyncio.run(service.ingest_uploaded_document(None, tenant_b, document_b, pipeline=pipeline))
    assert set(result_a.vector_ids).isdisjoint(result_b.vector_ids)
    stored_a = pipeline.store.vectorstore.get(where={"tenant_id": str(tenant_a)})
    stored_b = pipeline.store.vectorstore.get(where={"tenant_id": str(tenant_b)})
    assert stored_a["ids"] == result_a.vector_ids
    assert stored_b["ids"] == result_b.vector_ids
    assert all(metadata["document_id"] == str(document_a) for metadata in stored_a["metadatas"])
    assert all(metadata["document_id"] == str(document_b) for metadata in stored_b["metadatas"])


def test_staged_file_that_grew_past_upload_limit_is_rejected(tmp_path, monkeypatch):
    tenant_id, document_id = uuid4(), uuid4()
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    save_upload(tenant_id, document_id, "txt", b"a" * (5 * 1024 * 1024 + 1))
    document = make_document(tenant_id, document_id, "txt")

    async def get_document(_session, _tenant, _document):
        return document

    monkeypatch.setattr(service.document_repository, "get_document_by_id", get_document)
    pipeline = make_pipeline(tmp_path)
    with pytest.raises(ValueError, match="File too large"):
        asyncio.run(service.ingest_uploaded_document(None, tenant_id, document_id, pipeline=pipeline))
    assert pipeline.store.vectorstore.get()["ids"] == []
