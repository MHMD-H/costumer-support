"""Conversation repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Conversation, Message


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
        .options(selectinload(Conversation.tenant), selectinload(Conversation.user))
    )
    return result.scalar_one_or_none()


async def list_conversations(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    status: str | None,
    limit: int,
    cursor_created_at: datetime | None,
    cursor_id: UUID | None,
) -> list[Conversation]:
    criteria = [Conversation.tenant_id == tenant_id, Conversation.surface == "dashboard"]
    if status is not None:
        criteria.append(Conversation.status == status)
    if cursor_created_at is not None and cursor_id is not None:
        criteria.append(
            tuple_(Conversation.created_at, Conversation.id) < tuple_(cursor_created_at, cursor_id)
        )

    statement = select(Conversation).where(*criteria).order_by(Conversation.created_at.desc(), Conversation.id.desc())
    result = await session.execute(statement.limit(limit + 1))
    return list(result.scalars().all())


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


async def update_conversation(session: AsyncSession, conversation: Conversation, updates: dict) -> Conversation:
    for field, value in updates.items():
        setattr(conversation, field, value)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def get_message_by_id(session: AsyncSession, tenant_id: UUID, message_id: UUID) -> Message | None:
    result = await session.execute(
        select(Message)
        .options(selectinload(Message.tenant), selectinload(Message.conversation))
        .where(Message.tenant_id == tenant_id, Message.id == message_id)
    )
    return result.scalar_one_or_none()


async def list_messages(
    session: AsyncSession,
    tenant_id: UUID,
    conversation_id: UUID,
    *,
    limit: int,
    cursor_created_at: datetime | None,
    cursor_id: UUID | None,
) -> list[Message]:
    criteria = [Message.tenant_id == tenant_id, Message.conversation_id == conversation_id]
    if cursor_created_at is not None and cursor_id is not None:
        criteria.append(tuple_(Message.created_at, Message.id) < tuple_(cursor_created_at, cursor_id))

    statement = (
        select(Message)
        .options(selectinload(Message.tenant), selectinload(Message.conversation))
        .where(*criteria)
        .order_by(Message.created_at.desc(), Message.id.desc())
    )
    result = await session.execute(statement.limit(limit + 1))
    return list(result.scalars().all())


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
