"""Task 22 status, chunk, retry, and tenant boundaries."""

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document as LangChainDocument

from app.db.models import Document, DocumentChunk
from app.core.auth import get_current_dashboard_user
from app.db.postgres import get_db_session
from app.features import documents as service
from app.features.document_uploads import save_upload, upload_path
from app.features.schemas import DocumentUpdateRequest
from app.features.mock_services import mock_auth_user
from app.main import create_app
from rag.chunking import SourceAwareChunker
from rag.core.config import RagSettings
from rag.ingestion import IngestionPipeline
from rag.vectorstores import ChromaStore


class DeterministicEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[float(len(text)), 1.0] for text in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def make_pipeline(tmp_path):
    return IngestionPipeline(
        chunker=SourceAwareChunker(RagSettings(chunk_size=80, chunk_overlap=10)),
        store=ChromaStore(DeterministicEmbeddings(), collection_name="task22", persist_directory=tmp_path / "chroma"),
    )


def make_document(tenant_id, document_id, extension):
    now = datetime.now(timezone.utc)
    return Document(
        id=document_id, tenant_id=tenant_id, uploaded_by_user_id=uuid4(),
        title="Refund Policy", type=extension, source=f"policy.{extension}",
        visibility="internal", status="uploaded", metadata_={},
        created_at=now, updated_at=now,
    )


def install_repository(monkeypatch, document):
    rows = []
    failures = []

    async def claim(_session, tenant_id, document_id):
        if (tenant_id, document_id) != (document.tenant_id, document.id):
            return None
        if document.status not in {"uploaded", "failed"}:
            return None
        document.status = "processing"
        rows.clear()
        return document

    async def get(_session, tenant_id, document_id):
        return document if (tenant_id, document_id) == (document.tenant_id, document.id) else None

    async def complete(_session, claimed, chunks):
        assert claimed is document
        rows.extend(chunks)
        document.status = "ready"
        document.metadata_.pop("failure_reason", None)

    async def fail(_session, claimed, reason):
        assert claimed is document
        rows.clear()
        failures.append(reason)
        document.status = "failed"
        document.metadata_["failure_reason"] = reason

    monkeypatch.setattr(service.document_repository, "claim_document_for_processing", claim)
    monkeypatch.setattr(service.document_repository, "get_document_by_id", get)
    monkeypatch.setattr(service.document_repository, "complete_document_processing", complete)
    monkeypatch.setattr(service.document_repository, "fail_document_processing", fail)
    return rows, failures


def test_uploaded_file_becomes_ready_with_visible_chunk_ids(tmp_path, monkeypatch):
    tenant_id, document_id = uuid4(), uuid4()
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    save_upload(tenant_id, document_id, "txt", b"Refunds within 30 days.")
    document = make_document(tenant_id, document_id, "txt")
    rows, failures = install_repository(monkeypatch, document)
    pipeline = make_pipeline(tmp_path)

    assert asyncio.run(service.process_uploaded_document(None, tenant_id, document_id, pipeline=pipeline)) is True
    assert document.status == "ready"
    assert failures == []
    assert rows and all(row["metadata"]["tenant_id"] == str(tenant_id) for row in rows)
    assert all(row["metadata"]["document_id"] == str(document_id) for row in rows)
    assert all(row["chroma_vector_id"] == row["metadata"]["chroma_vector_id"] for row in rows)
    assert set(pipeline.store.vectorstore.get(ids=[row["chroma_vector_id"] for row in rows])["ids"]) == {
        row["chroma_vector_id"] for row in rows
    }


def test_failure_reason_is_safe_and_retry_replaces_partial_vectors(tmp_path, monkeypatch):
    tenant_id, document_id = uuid4(), uuid4()
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    save_upload(tenant_id, document_id, "txt", b"Initial policy text.")
    document = make_document(tenant_id, document_id, "txt")
    rows, failures = install_repository(monkeypatch, document)
    pipeline = make_pipeline(tmp_path)
    original_ingest = pipeline.ingest_source

    def fail_ingest(*args, **kwargs):
        pipeline.store.add_documents([LangChainDocument(
            page_content="Partial secret vector",
            metadata={
                "chunk_id": str(uuid4()),
                "chroma_vector_id": f"{document_id}:0",
                "tenant_id": str(tenant_id),
                "document_id": str(document_id),
            },
        )])
        raise RuntimeError("secret path and database credentials")

    pipeline.ingest_source = fail_ingest
    assert asyncio.run(service.process_uploaded_document(None, tenant_id, document_id, pipeline=pipeline)) is False
    assert document.status == "failed"
    assert failures == ["Document processing failed. Please retry."]
    assert "secret" not in document.metadata_["failure_reason"]
    assert rows == []
    assert pipeline.store.vectorstore.get()["ids"] == []

    pipeline.ingest_source = original_ingest
    assert asyncio.run(service.process_uploaded_document(None, tenant_id, document_id, pipeline=pipeline)) is True
    assert document.status == "ready" and "failure_reason" not in document.metadata_
    assert rows and pipeline.store.vectorstore.get(ids=[row["chroma_vector_id"] for row in rows])["ids"]


def test_cross_tenant_claim_cannot_touch_vectors(tmp_path, monkeypatch):
    tenant_id, document_id, attacker_id = uuid4(), uuid4(), uuid4()
    document = make_document(tenant_id, document_id, "txt")
    rows, _ = install_repository(monkeypatch, document)
    pipeline = make_pipeline(tmp_path)

    assert asyncio.run(service.process_uploaded_document(None, attacker_id, document_id, pipeline=pipeline)) is False
    assert document.status == "uploaded" and rows == []
    assert pipeline.store.vectorstore.get()["ids"] == []


def test_replacement_validates_and_stages_new_revision(tmp_path, monkeypatch):
    tenant_id, document_id = uuid4(), uuid4()
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    save_upload(tenant_id, document_id, "txt", b"Old policy")
    document = make_document(tenant_id, document_id, "txt")
    document.status = "ready"
    rows = [{"content": "Old policy"}]

    async def get(_session, requested_tenant, requested_document):
        return document if (requested_tenant, requested_document) == (tenant_id, document_id) else None

    async def mark(_session, claimed, updates):
        assert claimed is document
        rows.clear()
        for field, value in updates.items():
            setattr(document, field, value)
        document.status = "uploaded"

    async def count(_session, _tenant, _document):
        return len(rows)

    monkeypatch.setattr(service.document_repository, "get_document_by_id", get)
    monkeypatch.setattr(service.document_repository, "lock_document_for_replacement", get)
    monkeypatch.setattr(service.document_repository, "mark_document_uploaded", mark)
    monkeypatch.setattr(service.document_repository, "count_document_chunks", count)

    response = asyncio.run(service.replace_document_content(
        None, tenant_id, document_id,
        file=UploadFile(filename="../new.txt", file=BytesIO(b"New policy")),
        title=None, visibility="public",
    ))
    revision = document.metadata_["upload_revision"]
    assert response.status == "uploaded" and response.chunk_count == 0
    assert response.visibility == "public" and response.source == "new.txt"
    assert upload_path(tenant_id, document_id, "txt", UUID(revision)).read_bytes() == b"New policy"
    assert not upload_path(tenant_id, document_id, "txt").exists()

    indexed_rows, _ = install_repository(monkeypatch, document)
    pipeline = make_pipeline(tmp_path)
    assert asyncio.run(service.process_uploaded_document(None, tenant_id, document_id, pipeline=pipeline)) is True
    assert indexed_rows and all("New policy" in row["content"] for row in indexed_rows)
    assert pipeline.store.vectorstore.get()["documents"] == ["New policy"]

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.replace_document_content(
            None, uuid4(), document_id,
            file=UploadFile(filename="new.txt", file=BytesIO(b"Another policy")),
            title=None, visibility=None,
        ))
    assert exc.value.status_code == 404


def test_retry_requires_failed_document_and_trusted_tenant(monkeypatch):
    tenant_id, document_id = uuid4(), uuid4()
    document = make_document(tenant_id, document_id, "txt")
    document.status = "failed"
    document.metadata_["failure_reason"] = "Document processing failed. Please retry."

    async def get(_session, requested_tenant, requested_document):
        return document if (requested_tenant, requested_document) == (tenant_id, document_id) else None

    async def queue(_session, requested_tenant, requested_document):
        if (requested_tenant, requested_document) != (tenant_id, document_id) or document.status != "failed":
            return False
        document.status = "uploaded"
        return True

    async def count(_session, _tenant, _document):
        return 0

    monkeypatch.setattr(service.document_repository, "get_document_by_id", get)
    monkeypatch.setattr(service.document_repository, "queue_failed_document", queue)
    monkeypatch.setattr(service.document_repository, "count_document_chunks", count)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.retry_document(None, uuid4(), document_id))
    assert exc.value.status_code == 404
    response = asyncio.run(service.retry_document(None, tenant_id, document_id))
    assert response.status == "uploaded"
    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.retry_document(None, tenant_id, document_id))
    assert exc.value.status_code == 409


def test_manual_ready_and_reserved_metadata_are_rejected(monkeypatch):
    tenant_id, document_id = uuid4(), uuid4()
    document = make_document(tenant_id, document_id, "txt")

    async def get(_session, _tenant, _document):
        return document

    monkeypatch.setattr(service.document_repository, "get_document_by_id", get)
    for request in (
        DocumentUpdateRequest(status="ready"),
        DocumentUpdateRequest(metadata={"upload_revision": str(uuid4())}),
        DocumentUpdateRequest(metadata={"failure_reason": "ready"}),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(service.update_document(None, tenant_id, document_id, request))
        assert exc.value.status_code == 400


def test_api_upload_to_ready_and_visible_chunks(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    user = mock_auth_user()
    document_by_id = {}
    chunk_by_document = {}
    app = create_app()
    app.dependency_overrides[get_current_dashboard_user] = lambda: user

    async def session():
        yield None

    app.dependency_overrides[get_db_session] = session

    async def get_user(_session, tenant_id, user_id):
        return user if (tenant_id, user_id) == (user.tenant_id, user.id) else None

    async def create(_session, **kwargs):
        document = make_document(kwargs["tenant_id"], kwargs["document_id"], kwargs["document_type"])
        document.uploaded_by_user_id = kwargs["uploaded_by_user_id"]
        document.title = kwargs["title"]
        document.source = kwargs["source"]
        document.visibility = kwargs["visibility"]
        document_by_id[document.id] = document
        return document

    async def get(_session, tenant_id, document_id):
        document = document_by_id.get(document_id)
        return document if document and document.tenant_id == tenant_id else None

    async def claim(_session, tenant_id, document_id):
        document = await get(_session, tenant_id, document_id)
        if document is None or document.status != "uploaded":
            return None
        document.status = "processing"
        chunk_by_document[document_id] = []
        return document

    async def complete(_session, document, chunks):
        now = datetime.now(timezone.utc)
        chunk_by_document[document.id] = [DocumentChunk(
            id=uuid4(), tenant_id=document.tenant_id, document_id=document.id,
            chunk_index=chunk["chunk_index"], content=chunk["content"],
            visibility=document.visibility, chroma_collection=chunk["chroma_collection"],
            chroma_vector_id=chunk["chroma_vector_id"], metadata_=chunk["metadata"],
            created_at=now,
        ) for chunk in chunks]
        document.status = "ready"

    async def count(_session, tenant_id, document_id):
        return len(chunk_by_document.get(document_id, [])) if tenant_id == user.tenant_id else 0

    async def list_chunks(_session, tenant_id, document_id, *, limit, offset):
        rows = chunk_by_document.get(document_id, []) if tenant_id == user.tenant_id else []
        return rows[offset:offset + limit], len(rows)

    monkeypatch.setattr(service.user_repository, "get_user_by_id", get_user)
    monkeypatch.setattr(service.document_repository, "create_document", create)
    monkeypatch.setattr(service.document_repository, "get_document_by_id", get)
    monkeypatch.setattr(service.document_repository, "claim_document_for_processing", claim)
    monkeypatch.setattr(service.document_repository, "complete_document_processing", complete)
    monkeypatch.setattr(service.document_repository, "count_document_chunks", count)
    monkeypatch.setattr(service.document_repository, "list_document_chunks", list_chunks)

    with TestClient(app) as client:
        uploaded = client.post("/documents", files={"file": ("policy.txt", b"Refunds within 30 days", "text/plain")})
        assert uploaded.status_code == 201 and uploaded.json()["status"] == "uploaded"
        document_id = UUID(uploaded.json()["id"])
        assert asyncio.run(service.process_uploaded_document(None, user.tenant_id, document_id, pipeline=make_pipeline(tmp_path)))
        detail = client.get(f"/documents/{document_id}")
        chunks = client.get(f"/documents/{document_id}/chunks")
        assert detail.status_code == 200 and detail.json()["status"] == "ready"
        assert detail.json()["chunk_count"] == 1
        assert chunks.status_code == 200 and chunks.json()["items"][0]["content"] == "Refunds within 30 days"
        assert chunks.json()["items"][0]["metadata"]["tenant_id"] == str(user.tenant_id)
