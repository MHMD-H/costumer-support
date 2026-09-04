"""Order use cases."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order
from app.db.repositories import orders as order_repository
from app.features.pagination import page
from app.features.schemas import OrderListResponse, OrderResponse


def to_order_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        user_id=order.user_id,
        status=order.status,
        total_amount=order.total_amount,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


async def list_orders(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    status: str | None,
    user_id: UUID | None,
    limit: int,
    offset: int,
) -> OrderListResponse:
    orders, total = await order_repository.list_orders(
        session,
        tenant_id,
        status=status,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return OrderListResponse(
        items=[to_order_response(order) for order in orders],
        page=page(limit, offset, total),
    )


async def get_order(session: AsyncSession, tenant_id: UUID, order_id: UUID) -> OrderResponse:
    order = await order_repository.get_order_by_id(session, tenant_id, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Order was not found."},
        )
    return to_order_response(order)
