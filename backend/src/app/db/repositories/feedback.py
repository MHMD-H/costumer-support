"""Feedback repository."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Feedback


async def create_feedback(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID | None,
    conversation_id: UUID,
    message_id: UUID,
    surface: str,
    rating: int,
    comment: str | None,
) -> Feedback:
    feedback = Feedback(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        message_id=message_id,
        surface=surface,
        rating=rating,
        comment=comment,
    )
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)
    return feedback
