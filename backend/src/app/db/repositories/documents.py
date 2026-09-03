"""Document metadata repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk
from app.db.repositories.common import count_for_statement


async def get_document_by_id(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> Document | None:
    result = await session.execute(
        select(Document).where(Document.tenant_id == tenant_id, Document.id == document_id)
    )
    return result.scalar_one_or_none()


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

    statement = select(Document).where(*criteria).order_by(Document.created_at.desc())
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def create_document(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    uploaded_by_user_id: UUID,
    title: str,
    document_type: str,
    source: str,
    visibility: str,
    metadata: dict,
) -> Document:
    document = Document(
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
        .where(DocumentChunk.tenant_id == tenant_id, DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total
