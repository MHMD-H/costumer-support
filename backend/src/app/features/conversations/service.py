"""Conversation workflows."""

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message
from app.db.repositories import conversations as conversation_repository
from app.db.repositories import users as user_repository
from app.features.pagination import page
from app.features.schemas import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    MessageListResponse,
    MessageResponse,
    SourceRef,
)


def to_conversation_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        tenant_id=conversation.tenant_id,
        user_id=conversation.user_id,
        surface=conversation.surface,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def source_refs_from_json(sources: list[Any]) -> list[SourceRef]:
    refs: list[SourceRef] = []
    for source in sources:
        try:
            refs.append(SourceRef.model_validate(source))
        except ValidationError:
            continue
    return refs


def to_message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender=message.sender,
        content=message.content,
        sources=source_refs_from_json(message.sources),
        created_at=message.created_at,
    )


async def list_conversations(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    status: str | None,
    limit: int,
    offset: int,
) -> ConversationListResponse:
    conversations, total = await conversation_repository.list_conversations(
        session,
        tenant_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return ConversationListResponse(
        items=[to_conversation_response(conversation) for conversation in conversations],
        page=page(limit, offset, total),
    )


async def create_conversation(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    request: ConversationCreateRequest,
) -> ConversationResponse:
    user = await user_repository.get_user_by_id(session, tenant_id, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Conversation user was not found."},
        )

    conversation = await conversation_repository.create_conversation(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        title=request.title,
    )
    return to_conversation_response(conversation)


async def get_conversation(
    session: AsyncSession,
    tenant_id: UUID,
    conversation_id: UUID,
) -> ConversationResponse:
    conversation = await conversation_repository.get_conversation_by_id(
        session,
        tenant_id,
        conversation_id,
    )
    if conversation is None or conversation.surface != "dashboard":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Conversation was not found."},
        )
    return to_conversation_response(conversation)


async def list_messages(
    session: AsyncSession,
    tenant_id: UUID,
    conversation_id: UUID,
    *,
    limit: int,
    offset: int,
) -> MessageListResponse:
    conversation = await conversation_repository.get_conversation_by_id(
        session,
        tenant_id,
        conversation_id,
    )
    if conversation is None or conversation.surface != "dashboard":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Conversation was not found."},
        )

    messages, total = await conversation_repository.list_messages(
        session,
        tenant_id,
        conversation_id,
        limit=limit,
        offset=offset,
    )
    return MessageListResponse(
        items=[to_message_response(message) for message in messages],
        page=page(limit, offset, total),
    )


async def create_message(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    conversation_id: UUID,
    sender: str,
    content: str,
    sources: list[Any] | None = None,
    used_tools: list[Any] | None = None,
) -> MessageResponse:
    conversation = await conversation_repository.get_conversation_by_id(
        session,
        tenant_id,
        conversation_id,
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Conversation was not found."},
        )

    message = await conversation_repository.create_message(
        session,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        sender=sender,
        content=content,
        sources=sources or [],
        used_tools=used_tools or [],
    )
    return to_message_response(message)
