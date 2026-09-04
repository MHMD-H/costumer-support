"""Feedback use cases."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Feedback
from app.db.repositories import conversations as conversation_repository
from app.db.repositories import feedback as feedback_repository
from app.features.schemas import FeedbackCreateRequest, FeedbackResponse, FeedbackUpdateRequest


def to_feedback_response(feedback: Feedback) -> FeedbackResponse:
    return FeedbackResponse(
        id=feedback.id,
        user_id=feedback.user_id,
        conversation_id=feedback.conversation_id,
        message_id=feedback.message_id,
        rating=feedback.rating,
        comment=feedback.comment,
        created_at=feedback.created_at,
    )


async def create_feedback(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    request: FeedbackCreateRequest,
) -> FeedbackResponse:
    conversation = await conversation_repository.get_conversation_by_id(
        session,
        tenant_id,
        request.conversation_id,
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Conversation was not found."},
        )

    message = await conversation_repository.get_message_by_id(
        session,
        tenant_id,
        request.message_id,
    )
    if message is None or message.conversation_id != request.conversation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Message was not found for this conversation."},
        )

    feedback = await feedback_repository.create_feedback(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=request.conversation_id,
        message_id=request.message_id,
        surface=conversation.surface,
        rating=request.rating,
        comment=request.comment,
    )
    return to_feedback_response(feedback)


async def update_feedback(
    session: AsyncSession,
    tenant_id: UUID,
    feedback_id: UUID,
    request: FeedbackUpdateRequest,
) -> FeedbackResponse:
    feedback = await feedback_repository.get_feedback_by_id(session, tenant_id, feedback_id)
    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Feedback was not found."},
        )

    updates = request.model_dump(exclude_unset=True)
    if updates.get("rating") is None:
        updates.pop("rating", None)
    if updates:
        feedback = await feedback_repository.update_feedback(session, feedback, updates)
    return to_feedback_response(feedback)
