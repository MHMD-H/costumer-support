"""Document metadata repository."""

from uuid import UUID

from datetime import datetime, timezone

from sqlalchemy import case, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Document, DocumentChunk
from app.db.repositories.common import count_for_statement


async def get_document_by_id(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> Document | None:
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.tenant), selectinload(Document.uploaded_by_user))
        .where(Document.tenant_id == tenant_id, Document.id == document_id)
    )
    return result.scalar_one_or_none()


async def lock_document_for_replacement(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> Document | None:
    result = await session.execute(
        select(Document).where(Document.tenant_id == tenant_id, Document.id == document_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def mark_document_uploaded(session: AsyncSession, document: Document, updates: dict) -> None:
    await session.execute(delete(DocumentChunk).where(
        DocumentChunk.tenant_id == document.tenant_id, DocumentChunk.document_id == document.id,
    ))
    for field, value in updates.items():
        setattr(document, field, value)
    document.status = "uploaded"
    document.updated_at = datetime.now(timezone.utc)
    await session.commit()


async def queue_failed_document(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> bool:
    result = await session.execute(
        update(Document)
        .where(Document.tenant_id == tenant_id, Document.id == document_id, Document.status == "failed")
        .values(status="uploaded", updated_at=datetime.now(timezone.utc))
        .returning(Document.id)
    )
    queued = result.scalar_one_or_none() is not None
    if queued:
        await session.commit()
    else:
        await session.rollback()
    return queued


async def requeue_interrupted_documents(session: AsyncSession) -> int:
    """Called only by the singleton worker after it acquires its advisory lock."""
    result = await session.execute(
        update(Document)
        .where(Document.status == "processing")
        .values(status="uploaded", updated_at=datetime.now(timezone.utc))
    )
    await session.commit()
    return result.rowcount


async def next_uploaded_document(
    session: AsyncSession,
    previous_tenant_id: UUID | None = None,
) -> tuple[UUID, UUID] | None:
    statement = select(Document.tenant_id, Document.id).where(
        Document.status == "uploaded", Document.type.in_(("txt", "pdf", "docx"))
    )
    if previous_tenant_id is not None:
        statement = statement.order_by(
            case((Document.tenant_id == previous_tenant_id, 1), else_=0)
        )
    result = await session.execute(statement.order_by(Document.created_at, Document.id).limit(1))
    row = result.first()
    return (row.tenant_id, row.id) if row else None


async def list_documents(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    document_type: str | None,
    status: str | None,
    visibility: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Document], int]:
    criteria = [Document.tenant_id == tenant_id]
    if document_type is not None:
        criteria.append(Document.type == document_type)
    if status is not None:
        criteria.append(Document.status == status)
    if visibility is not None:
        criteria.append(Document.visibility == visibility)

    statement = select(Document).where(*criteria).order_by(Document.created_at.desc(), Document.id.desc())
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def create_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    tenant_id: UUID,
    uploaded_by_user_id: UUID,
    title: str,
    document_type: str,
    source: str,
    visibility: str,
    metadata: dict,
) -> Document:
    document = Document(
        id=document_id,
        tenant_id=tenant_id,
        uploaded_by_user_id=uploaded_by_user_id,
        title=title,
        type=document_type,
        source=source,
        visibility=visibility,
        status="uploaded",
        metadata_=metadata,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def update_document(session: AsyncSession, document: Document, updates: dict) -> Document:
    for field, value in updates.items():
        setattr(document, field, value)
    await session.commit()
    await session.refresh(document)
    return document


async def count_document_chunks(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> int:
    statement = select(DocumentChunk).where(
        DocumentChunk.tenant_id == tenant_id,
        DocumentChunk.document_id == document_id,
    )
    return await count_for_statement(session, statement)


async def list_document_chunks(
    session: AsyncSession,
    tenant_id: UUID,
    document_id: UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[DocumentChunk], int]:
    statement = (
        select(DocumentChunk)
        .options(selectinload(DocumentChunk.document))
        .where(DocumentChunk.tenant_id == tenant_id, DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.created_at.desc(), DocumentChunk.id.desc())
    )
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def replace_document_chunks(
    session: AsyncSession,
    document: Document,
    chunks: list[dict],
) -> Document:
    await session.execute(
        delete(DocumentChunk).where(
            DocumentChunk.tenant_id == document.tenant_id,
            DocumentChunk.document_id == document.id,
        )
    )
    for chunk in chunks:
        session.add(
            DocumentChunk(
                tenant_id=document.tenant_id,
                document_id=document.id,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                visibility=document.visibility,
                chroma_collection=chunk["chroma_collection"],
                chroma_vector_id=chunk["chroma_vector_id"],
                metadata_=chunk["metadata"],
            )
        )
    await session.commit()
    await session.refresh(document)
    return document


async def claim_document_for_processing(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> Document | None:
    """Claim a pending document once, clearing previously visible chunk rows."""
    claimed = await session.execute(
        update(Document)
        .where(Document.tenant_id == tenant_id, Document.id == document_id, Document.status.in_(("uploaded", "failed")))
        .values(status="processing", updated_at=datetime.now(timezone.utc))
        .returning(Document.id)
    )
    if claimed.scalar_one_or_none() is None:
        await session.rollback()
        return None
    await session.execute(delete(DocumentChunk).where(
        DocumentChunk.tenant_id == tenant_id, DocumentChunk.document_id == document_id,
    ))
    await session.commit()
    return await get_document_by_id(session, tenant_id, document_id)


async def complete_document_processing(
    session: AsyncSession, document: Document, chunks: list[dict],
) -> None:
    """Publish chunk rows and the ready state in one PostgreSQL transaction."""
    for chunk in chunks:
        session.add(DocumentChunk(
            tenant_id=document.tenant_id,
            document_id=document.id,
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            visibility=document.visibility,
            chroma_collection=chunk["chroma_collection"],
            chroma_vector_id=chunk["chroma_vector_id"],
            metadata_=chunk["metadata"],
        ))
    document.status = "ready"
    document.metadata_ = {key: value for key, value in (document.metadata_ or {}).items() if key != "failure_reason"}
    document.updated_at = datetime.now(timezone.utc)
    await session.commit()


async def fail_document_processing(session: AsyncSession, document: Document, reason: str) -> None:
    await session.rollback()
    document = await get_document_by_id(session, document.tenant_id, document.id)
    if document is None:
        return
    await session.execute(delete(DocumentChunk).where(
        DocumentChunk.tenant_id == document.tenant_id, DocumentChunk.document_id == document.id,
    ))
    document.status = "failed"
    document.metadata_ = {**(document.metadata_ or {}), "failure_reason": reason}
    document.updated_at = datetime.now(timezone.utc)
    await session.commit()
