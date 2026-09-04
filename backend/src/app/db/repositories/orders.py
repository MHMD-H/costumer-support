"""Order repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order
from app.db.repositories.common import count_for_statement


async def get_order_by_id(session: AsyncSession, tenant_id: UUID, order_id: UUID) -> Order | None:
    result = await session.execute(
        select(Order).where(Order.tenant_id == tenant_id, Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def list_orders(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    status: str | None,
    user_id: UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Order], int]:
    criteria = [Order.tenant_id == tenant_id]
    if status is not None:
        criteria.append(Order.status == status)
    if user_id is not None:
        criteria.append(Order.user_id == user_id)

    statement = select(Order).where(*criteria).order_by(Order.created_at.desc())
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total
