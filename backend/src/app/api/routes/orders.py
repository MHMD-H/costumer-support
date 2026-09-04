"""Order API routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features.commerce import orders as order_service
from app.features.schemas import OrderListResponse, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")
async def list_orders(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: Literal["pending", "paid", "fulfilled", "cancelled", "refunded"] | None = None,
    user_id: UUID | None = None,
) -> OrderListResponse:
    return await order_service.list_orders(
        session,
        tenant.tenant_id,
        status=status,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{order_id}")
async def get_order(
    order_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> OrderResponse:
    return await order_service.get_order(session, tenant.tenant_id, order_id)
