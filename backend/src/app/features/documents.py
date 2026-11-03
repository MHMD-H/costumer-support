"""Document metadata use cases."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk
from app.db.repositories import documents as document_repository
from app.db.repositories import users as user_repository
from app.features.pagination import offset_pagination
from app.features.schemas import (
    DocumentChunkListResponse,
    DocumentChunkResponse,
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
)
from app.features.document_uploads import MAX_UPLOAD_BYTES, read_validated_upload, save_upload, remove_upload, upload_path
from rag.vectorstores.chroma import normalize_chroma_metadata

if TYPE_CHECKING:
    from rag.ingestion import IngestionPipeline, IngestionResult


logger = logging.getLogger(__name__)


async def to_document_response(session: AsyncSession, document: Document) -> DocumentResponse:
    chunk_count = await document_repository.count_document_chunks(session, document.tenant_id, document.id)
    return DocumentResponse(
        id=document.id,
        tenant_id=document.tenant_id,
        title=document.title,
        type=document.type,
        source=document.source,
        visibility=document.visibility,
        status=document.status,
        chunk_count=chunk_count,
        failure_reason=(document.metadata_ or {}).get("failure_reason") if document.status == "failed" else None,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def to_document_create_response(document: Document) -> DocumentCreateResponse:
    return DocumentCreateResponse(
        id=document.id,
        tenant_id=document.tenant_id,
        title=document.title,
        type=document.type,
        source=document.source,
        visibility=document.visibility,
        status=document.status,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def to_document_chunk_response(chunk: DocumentChunk) -> DocumentChunkResponse:
    return DocumentChunkResponse(
        id=chunk.id,
        document_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        metadata=chunk.metadata_,
        created_at=chunk.created_at,
    )


async def list_documents(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    document_type: str | None,
    status: str | None,
    visibility: str | None,
    limit: int,
    offset: int,
) -> DocumentListResponse:
    documents, total = await document_repository.list_documents(
        session,
        tenant_id,
        document_type=document_type,
        status=status,
        visibility=visibility,
        limit=limit,
        offset=offset,
    )
    return offset_pagination(
        DocumentListResponse,
        [await to_document_response(session, document) for document in documents],
        limit=limit,
        offset=offset,
        total=total,
    )


async def create_document(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    uploaded_by_user_id: UUID,
    file: UploadFile,
    title: str | None,
    visibility: str,
) -> DocumentCreateResponse:
    user = await user_repository.get_user_by_id(session, tenant_id, uploaded_by_user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Uploading user was not found."},
        )

    filename, document_type, content = await read_validated_upload(file)
    document_id = uuid4()
    try:
        save_upload(tenant_id, document_id, document_type, content)
        document = await document_repository.create_document(
            session,
            document_id=document_id,
            tenant_id=tenant_id,
            uploaded_by_user_id=uploaded_by_user_id,
            title=title or filename,
            document_type=document_type,
            source=filename,
            visibility=visibility,
            metadata={},
        )
    except Exception:
        remove_upload(tenant_id, document_id, document_type)
        raise
    return to_document_create_response(document)


async def ingest_uploaded_document(
    session: AsyncSession,
    tenant_id: UUID,
    document_id: UUID,
    *,
    pipeline: "IngestionPipeline",
    replace: bool = False,
) -> "IngestionResult":
    """Index one accepted file through the shared LangChain pipeline."""
    document = await document_repository.get_document_by_id(session, tenant_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Document was not found."},
        )
    if document.status not in {"uploaded", "processing"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "conflict", "message": "Document is not ready for ingestion."},
        )
    if document.type not in {"txt", "pdf", "docx"}:
        raise ValueError("Uploaded document type is unsupported")

    revision_value = (document.metadata_ or {}).get("upload_revision")
    revision = UUID(revision_value) if revision_value else None
    path = upload_path(tenant_id, document_id, document.type, revision)
    return await asyncio.to_thread(
        pipeline.ingest_source,
        path,
        tenant_id=str(tenant_id),
        source_type=document.type,
        document_id=str(document_id),
        replace=replace,
        source_name=document.source.replace("\\", "/").rsplit("/", 1)[-1],
        title=document.title,
        visibility=document.visibility,
        max_bytes=MAX_UPLOAD_BYTES,
    )


async def process_uploaded_document(
    session: AsyncSession, tenant_id: UUID, document_id: UUID, *, pipeline: "IngestionPipeline",
) -> bool:
    """Claim, index, and publish one document; failures remain visible as status."""
    document = await document_repository.claim_document_for_processing(session, tenant_id, document_id)
    if document is None:
        return False
    try:
        # A retry can follow a crash after a partial Chroma write. Remove only this tenant's vectors.
        await asyncio.to_thread(pipeline.store.delete_document, tenant_id=str(tenant_id), document_id=str(document_id))
        result = await ingest_uploaded_document(session, tenant_id, document_id, pipeline=pipeline, replace=True)
        if result.document_ids != [str(document_id)] or not result.chunks or len(result.chunks) != len(result.vector_ids):
            raise ValueError("Ingestion produced inconsistent document or chunk identities")
        chunks = []
        for chunk, vector_id in zip(result.chunks, result.vector_ids, strict=True):
            metadata = chunk.metadata
            if (metadata.get("tenant_id") != str(tenant_id)
                    or metadata.get("document_id") != str(document_id)
                    or metadata.get("chroma_vector_id") != vector_id):
                raise ValueError("Ingestion produced inconsistent vector metadata")
            chunks.append({
                "chunk_index": int(metadata["chunk_index"]),
                "content": chunk.page_content,
                "chroma_collection": pipeline.store.collection_name,
                "chroma_vector_id": vector_id,
                "metadata": normalize_chroma_metadata(metadata),
            })
        await document_repository.complete_document_processing(session, document, chunks)
        return True
    except Exception:
        logger.exception("Document ingestion failed for tenant=%s document=%s", tenant_id, document_id)
        try:
            await asyncio.to_thread(pipeline.store.delete_document, tenant_id=str(tenant_id), document_id=str(document_id))
        except Exception:
            logger.exception("Could not clear vectors after failed ingestion for document=%s", document_id)
        await document_repository.fail_document_processing(session, document, "Document processing failed. Please retry.")
        return False


async def get_document(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> DocumentResponse:
    document = await document_repository.get_document_by_id(session, tenant_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Document was not found."},
        )
    return await to_document_response(session, document)


async def update_document(
    session: AsyncSession,
    tenant_id: UUID,
    document_id: UUID,
    request: DocumentUpdateRequest,
) -> DocumentResponse:
    document = await document_repository.get_document_by_id(session, tenant_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Document was not found."},
        )

    if "status" in request.model_fields_set:
        raise HTTPException(status_code=400, detail={"error": "invalid_update", "message": "Processing status cannot be changed manually."})
    if request.metadata is not None and {"upload_revision", "failure_reason"} & request.metadata.keys():
        raise HTTPException(status_code=400, detail={"error": "invalid_update", "message": "Reserved document metadata cannot be changed."})
    if "visibility" in request.model_fields_set and document.status in {"processing", "ready"}:
        raise HTTPException(status_code=409, detail={"error": "conflict", "message": "Replace the file to change indexed visibility."})

    updates = {
        field: value
        for field, value in request.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if "metadata" in updates:
        incoming_metadata = updates.pop("metadata")
        internal_metadata = {key: value for key, value in (document.metadata_ or {}).items() if key in {"upload_revision", "failure_reason"}}
        updates["metadata_"] = {**incoming_metadata, **internal_metadata}
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        document = await document_repository.update_document(session, document, updates)
    return await to_document_response(session, document)


async def replace_document_content(
    session: AsyncSession,
    tenant_id: UUID,
    document_id: UUID,
    *,
    file: UploadFile,
    title: str | None,
    visibility: str | None,
) -> DocumentResponse:
    document = await document_repository.get_document_by_id(session, tenant_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Document was not found."},
        )

    filename, document_type, content = await read_validated_upload(file)
    locked = await document_repository.lock_document_for_replacement(session, tenant_id, document_id)
    if locked is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Document was not found."})
    if locked.status == "processing":
        await session.rollback()
        raise HTTPException(status_code=409, detail={"error": "conflict", "message": "Document is processing."})

    previous_type = locked.type
    previous_revision_value = (locked.metadata_ or {}).get("upload_revision")
    previous_revision = UUID(previous_revision_value) if previous_revision_value else None
    revision = uuid4()
    try:
        save_upload(tenant_id, document_id, document_type, content, revision)
        await document_repository.mark_document_uploaded(session, locked, {
            "title": title or filename,
            "type": document_type,
            "source": filename,
            "visibility": visibility or locked.visibility,
            "metadata_": {**{k: v for k, v in (locked.metadata_ or {}).items() if k not in {"failure_reason", "upload_revision"}}, "upload_revision": str(revision)},
        })
    except Exception:
        await session.rollback()
        remove_upload(tenant_id, document_id, document_type, revision)
        raise
    try:
        remove_upload(tenant_id, document_id, previous_type, previous_revision)
    except OSError:
        logger.exception("Could not remove superseded staged file for document=%s", document_id)
    return await to_document_response(session, locked)


async def retry_document(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> DocumentResponse:
    document = await document_repository.get_document_by_id(session, tenant_id, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Document was not found."})
    if not await document_repository.queue_failed_document(session, tenant_id, document_id):
        raise HTTPException(status_code=409, detail={"error": "conflict", "message": "Only failed documents can be retried."})
    document = await document_repository.get_document_by_id(session, tenant_id, document_id)
    return await to_document_response(session, document)


async def list_document_chunks(
    session: AsyncSession,
    tenant_id: UUID,
    document_id: UUID,
    *,
    limit: int,
    offset: int,
) -> DocumentChunkListResponse:
    document = await document_repository.get_document_by_id(session, tenant_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Document was not found."},
        )

    chunks, total = await document_repository.list_document_chunks(
        session,
        tenant_id,
        document_id,
        limit=limit,
        offset=offset,
    )
    return offset_pagination(
        DocumentChunkListResponse,
        [to_document_chunk_response(chunk) for chunk in chunks],
        limit=limit,
        offset=offset,
        total=total,
    )
