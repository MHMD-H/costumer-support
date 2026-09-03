"""Conversation repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message
from app.db.repositories.common import count_for_statement


async def get_conversation_by_id(
    session: AsyncSession,
    tenant_id: UUID,
    conversation_id: UUID,
) -> Conversation | None:
    result = await session.execute(
        select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.id == conversation_id,
        )
    )
    return result.scalar_one_or_none()


async def list_conversations(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Conversation], int]:
    criteria = [Conversation.tenant_id == tenant_id, Conversation.surface == "dashboard"]
    if status is not None:
        criteria.append(Conversation.status == status)

    statement = select(Conversation).where(*criteria).order_by(Conversation.created_at.desc())
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def create_conversation(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    title: str | None,
) -> Conversation:
    conversation = Conversation(
        tenant_id=tenant_id,
        user_id=user_id,
        surface="dashboard",
        title=title,
        status="active",
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def get_message_by_id(session: AsyncSession, tenant_id: UUID, message_id: UUID) -> Message | None:
    result = await session.execute(
        select(Message).where(Message.tenant_id == tenant_id, Message.id == message_id)
    )
    return result.scalar_one_or_none()


async def list_messages(
    session: AsyncSession,
    tenant_id: UUID,
    conversation_id: UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[Message], int]:
    statement = (
        select(Message)
        .where(Message.tenant_id == tenant_id, Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def create_message(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    conversation_id: UUID,
    sender: str,
    content: str,
    sources: list,
    used_tools: list,
) -> Message:
    message = Message(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        sender=sender,
        content=content,
        sources=sources,
        used_tools=used_tools,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message
