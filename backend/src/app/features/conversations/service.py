"""Conversation workflows."""

from typing import Any
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status as http_status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message
from app.db.repositories import conversations as conversation_repository
from app.db.repositories import users as user_repository
from app.features.pagination import decode_cursor, encode_cursor
from app.features.schemas import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdateRequest,
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
    cursor: str | None,
) -> ConversationListResponse:
    try:
        cursor_values = decode_cursor(cursor) if cursor is not None else None
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail={"error": "bad_request", "message": "Cursor is invalid."},
        ) from exc

    conversations = await conversation_repository.list_conversations(
        session,
        tenant_id,
        status=status,
        limit=limit,
        cursor_created_at=cursor_values[0] if cursor_values is not None else None,
        cursor_id=cursor_values[1] if cursor_values is not None else None,
    )
    has_more = len(conversations) > limit
    conversations = conversations[:limit]
    return ConversationListResponse(
        items=[to_conversation_response(conversation) for conversation in conversations],
        limit=limit,
        has_more=has_more,
        next_cursor=(
            encode_cursor(conversations[-1].created_at, conversations[-1].id)
            if has_more and conversations
            else None
        ),
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
            status_code=http_status.HTTP_404_NOT_FOUND,
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
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Conversation was not found."},
        )
    return to_conversation_response(conversation)


async def update_conversation(
    session: AsyncSession,
    tenant_id: UUID,
    conversation_id: UUID,
    request: ConversationUpdateRequest,
) -> ConversationResponse:
    conversation = await conversation_repository.get_conversation_by_id(
        session,
        tenant_id,
        conversation_id,
    )
    if conversation is None or conversation.surface != "dashboard":
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Conversation was not found."},
        )

    updates = request.model_dump(exclude_unset=True)
    if updates.get("status") is None:
        updates.pop("status", None)
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        conversation = await conversation_repository.update_conversation(session, conversation, updates)
    return to_conversation_response(conversation)


async def list_messages(
    session: AsyncSession,
    tenant_id: UUID,
    conversation_id: UUID,
    *,
    limit: int,
    cursor: str | None,
) -> MessageListResponse:
    conversation = await conversation_repository.get_conversation_by_id(
        session,
        tenant_id,
        conversation_id,
    )
    if conversation is None or conversation.surface != "dashboard":
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Conversation was not found."},
        )

    try:
        cursor_values = decode_cursor(cursor) if cursor is not None else None
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail={"error": "bad_request", "message": "Cursor is invalid."},
        ) from exc

    messages = await conversation_repository.list_messages(
        session,
        tenant_id,
        conversation_id,
        limit=limit,
        cursor_created_at=cursor_values[0] if cursor_values is not None else None,
        cursor_id=cursor_values[1] if cursor_values is not None else None,
    )
    has_more = len(messages) > limit
    messages = messages[:limit]
    return MessageListResponse(
        items=[to_message_response(message) for message in messages],
        limit=limit,
        has_more=has_more,
        next_cursor=(
            encode_cursor(messages[-1].created_at, messages[-1].id)
            if has_more and messages
            else None
        ),
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
            status_code=http_status.HTTP_404_NOT_FOUND,
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
