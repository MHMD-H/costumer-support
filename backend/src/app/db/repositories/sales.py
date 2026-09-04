"""Sales repository."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order, Sale


async def get_sales_summary(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    start_date: datetime | None,
    end_date: datetime | None,
    product_id: UUID | None,
) -> tuple[Decimal, int]:
    criteria = [Sale.tenant_id == tenant_id]
    if start_date is not None:
        criteria.append(Sale.created_at >= start_date)
    if end_date is not None:
        criteria.append(Sale.created_at <= end_date)
    if product_id is not None:
        criteria.append(Sale.product_id == product_id)

    statement = (
        select(
            func.coalesce(func.sum(Sale.amount), 0),
            func.count(func.distinct(Sale.order_id)),
        )
        .join(Order, Order.id == Sale.order_id)
        .where(*criteria, Order.tenant_id == tenant_id)
    )
    result = await session.execute(statement)
    total_revenue, order_count = result.one()
    return Decimal(total_revenue), int(order_count)
