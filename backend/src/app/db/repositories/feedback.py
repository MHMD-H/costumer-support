"""Feedback repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Feedback


async def get_feedback_by_id(session: AsyncSession, tenant_id: UUID, feedback_id: UUID) -> Feedback | None:
    result = await session.execute(
        select(Feedback).where(Feedback.tenant_id == tenant_id, Feedback.id == feedback_id)
    )
    return result.scalar_one_or_none()


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


async def update_feedback(session: AsyncSession, feedback: Feedback, updates: dict) -> Feedback:
    for field, value in updates.items():
        setattr(feedback, field, value)
    await session.commit()
    await session.refresh(feedback)
    return feedback
