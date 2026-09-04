"""Sales metric use cases."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import sales as sales_repository
from app.features.schemas import SalesSummaryRequest, SalesSummaryResponse


async def get_sales_summary(
    session: AsyncSession,
    tenant_id: UUID,
    request: SalesSummaryRequest,
) -> SalesSummaryResponse:
    total_revenue, order_count = await sales_repository.get_sales_summary(
        session,
        tenant_id,
        start_date=request.start_date,
        end_date=request.end_date,
        product_id=request.product_id,
    )
    average_order_value = Decimal("0.00")
    if order_count:
        average_order_value = total_revenue / Decimal(order_count)
    return SalesSummaryResponse(
        total_revenue=total_revenue,
        order_count=order_count,
        average_order_value=average_order_value,
    )
