"""Document metadata use cases."""

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk
from app.db.repositories import documents as document_repository
from app.db.repositories import users as user_repository
from app.features.pagination import page
from app.features.schemas import (
    DocumentChunkListResponse,
    DocumentChunkResponse,
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentResponse,
)


def document_type_for_filename(filename: str) -> str:
    extension = Path(filename).suffix.lower().lstrip(".")
    return extension if extension in {"pdf", "docx", "txt"} else "txt"


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
    return DocumentListResponse(
        items=[await to_document_response(session, document) for document in documents],
        page=page(limit, offset, total),
    )


async def create_document(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    uploaded_by_user_id: UUID,
    filename: str,
    title: str | None,
    visibility: str,
) -> DocumentCreateResponse:
    user = await user_repository.get_user_by_id(session, tenant_id, uploaded_by_user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Uploading user was not found."},
        )

    document = await document_repository.create_document(
        session,
        tenant_id=tenant_id,
        uploaded_by_user_id=uploaded_by_user_id,
        title=title or filename,
        document_type=document_type_for_filename(filename),
        source=filename,
        visibility=visibility,
        metadata={},
    )
    return to_document_create_response(document)


async def get_document(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> DocumentResponse:
    document = await document_repository.get_document_by_id(session, tenant_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Document was not found."},
        )
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
    return DocumentChunkListResponse(
        items=[to_document_chunk_response(chunk) for chunk in chunks],
        page=page(limit, offset, total),
    )
